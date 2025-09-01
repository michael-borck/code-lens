"""
Similarity analysis for detecting potential plagiarism in code submissions
"""

import ast
import difflib
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class SimilarityMethod(Enum):
    """Available similarity analysis methods"""
    AST_STRUCTURAL = "ast_structural"
    TOKEN_BASED = "token_based"
    LINE_BASED = "line_based"
    FUNCTION_SIGNATURE = "function_signature"
    VARIABLE_PATTERN = "variable_pattern"


@dataclass
class SimilarityMatch:
    """Represents a similarity match between code sections"""
    method: SimilarityMethod
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    matched_sections: dict[str, Any]
    explanation: str


@dataclass
class SimilarityResult:
    """Result of similarity analysis between two code submissions"""
    overall_score: float  # 0.0 to 1.0
    matches: list[SimilarityMatch]
    flagged: bool
    threshold_used: float
    methods_used: list[SimilarityMethod]

    # Detailed breakdown
    structural_similarity: float = 0.0
    token_similarity: float = 0.0
    line_similarity: float = 0.0
    function_similarity: float = 0.0


class PythonSimilarityAnalyzer:
    """Similarity analyzer specifically for Python code"""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def analyze_similarity(
        self,
        code1: str,
        code2: str,
        methods: list[SimilarityMethod] | None = None
    ) -> SimilarityResult:
        """
        Analyze similarity between two Python code submissions

        Args:
            code1: First code submission
            code2: Second code submission
            methods: Similarity methods to use (default: all)

        Returns:
            SimilarityResult with detailed similarity analysis
        """
        if methods is None:
            methods = list(SimilarityMethod)

        matches = []
        scores = {}

        try:
            # AST structural similarity
            if SimilarityMethod.AST_STRUCTURAL in methods:
                structural_match = self._analyze_ast_similarity(code1, code2)
                if structural_match:
                    matches.append(structural_match)
                    scores['structural'] = structural_match.score

            # Token-based similarity
            if SimilarityMethod.TOKEN_BASED in methods:
                token_match = self._analyze_token_similarity(code1, code2)
                if token_match:
                    matches.append(token_match)
                    scores['token'] = token_match.score

            # Line-based similarity
            if SimilarityMethod.LINE_BASED in methods:
                line_match = self._analyze_line_similarity(code1, code2)
                if line_match:
                    matches.append(line_match)
                    scores['line'] = line_match.score

            # Function signature similarity
            if SimilarityMethod.FUNCTION_SIGNATURE in methods:
                function_match = self._analyze_function_similarity(code1, code2)
                if function_match:
                    matches.append(function_match)
                    scores['function'] = function_match.score

            # Calculate overall score (weighted average)
            overall_score = self._calculate_overall_score(scores)

            result = SimilarityResult(
                overall_score=overall_score,
                matches=matches,
                flagged=overall_score >= self.threshold,
                threshold_used=self.threshold,
                methods_used=methods,
                structural_similarity=scores.get('structural', 0.0),
                token_similarity=scores.get('token', 0.0),
                line_similarity=scores.get('line', 0.0),
                function_similarity=scores.get('function', 0.0)
            )

            logger.info("Similarity analysis completed",
                       overall_score=overall_score,
                       flagged=result.flagged,
                       matches_count=len(matches))

            return result

        except Exception as e:
            logger.error("Similarity analysis failed", error=str(e))
            return SimilarityResult(
                overall_score=0.0,
                matches=[],
                flagged=False,
                threshold_used=self.threshold,
                methods_used=methods
            )

    def _analyze_ast_similarity(self, code1: str, code2: str) -> SimilarityMatch | None:
        """Analyze structural similarity using AST comparison"""
        try:
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)

            # Extract structural features
            features1 = self._extract_ast_features(tree1)
            features2 = self._extract_ast_features(tree2)

            # Compare structures
            similarity = self._compare_ast_features(features1, features2)

            if similarity > 0.1:  # Only report significant similarities
                return SimilarityMatch(
                    method=SimilarityMethod.AST_STRUCTURAL,
                    score=similarity,
                    confidence=0.9,  # AST comparison is highly reliable
                    matched_sections={
                        "common_patterns": self._find_common_ast_patterns(features1, features2)
                    },
                    explanation=f"Structural similarity: {similarity:.2f} based on AST analysis"
                )

        except SyntaxError:
            logger.warning("Syntax error in code - skipping AST analysis")
        except Exception as e:
            logger.error("AST similarity analysis failed", error=str(e))

        return None

    def _extract_ast_features(self, tree: ast.AST) -> dict[str, Any]:
        """Extract structural features from AST"""
        features = {
            'node_types': [],
            'function_names': [],
            'class_names': [],
            'control_structures': [],
            'nesting_pattern': [],
            'variable_names': set(),
            'import_modules': []
        }

        for node in ast.walk(tree):
            features['node_types'].append(type(node).__name__)

            if isinstance(node, ast.FunctionDef):
                features['function_names'].append(node.name)
            elif isinstance(node, ast.ClassDef):
                features['class_names'].append(node.name)
            elif isinstance(node, ast.If | ast.While | ast.For):
                features['control_structures'].append(type(node).__name__)
            elif isinstance(node, ast.Name):
                features['variable_names'].add(node.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    features['import_modules'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    features['import_modules'].append(node.module)

        # Convert set to list for comparison
        features['variable_names'] = list(features['variable_names'])

        return features

    def _compare_ast_features(self, features1: dict[str, Any], features2: dict[str, Any]) -> float:
        """Compare AST features and return similarity score"""
        total_score = 0.0
        weights = {
            'node_types': 0.3,
            'function_names': 0.2,
            'class_names': 0.15,
            'control_structures': 0.15,
            'variable_names': 0.1,
            'import_modules': 0.1
        }

        for feature, weight in weights.items():
            list1 = features1.get(feature, [])
            list2 = features2.get(feature, [])

            # Calculate Jaccard similarity for lists
            set1, set2 = set(list1), set(list2)
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))

            similarity = intersection / union if union > 0 else 0.0
            total_score += similarity * weight

        return total_score

    def _find_common_ast_patterns(self, features1: dict[str, Any], features2: dict[str, Any]) -> dict[str, list]:
        """Find common patterns in AST features"""
        common_patterns = {}

        for feature_type in ['function_names', 'class_names', 'control_structures']:
            list1 = features1.get(feature_type, [])
            list2 = features2.get(feature_type, [])
            common = list(set(list1).intersection(set(list2)))
            if common:
                common_patterns[feature_type] = common

        return common_patterns

    def _analyze_token_similarity(self, code1: str, code2: str) -> SimilarityMatch | None:
        """Analyze similarity based on code tokens"""
        try:
            # Tokenize code (simplified - split by whitespace and symbols)
            tokens1 = self._tokenize_code(code1)
            tokens2 = self._tokenize_code(code2)

            # Calculate token similarity using sequence matching
            matcher = difflib.SequenceMatcher(None, tokens1, tokens2)
            similarity = matcher.ratio()

            if similarity > 0.3:  # Only report significant token similarities
                common_tokens = self._find_common_token_sequences(tokens1, tokens2)

                return SimilarityMatch(
                    method=SimilarityMethod.TOKEN_BASED,
                    score=similarity,
                    confidence=0.7,
                    matched_sections={
                        "common_tokens": common_tokens[:10],  # First 10 common sequences
                        "total_common_tokens": len(common_tokens)
                    },
                    explanation=f"Token similarity: {similarity:.2f} based on code token analysis"
                )

        except Exception as e:
            logger.error("Token similarity analysis failed", error=str(e))

        return None

    def _tokenize_code(self, code: str) -> list[str]:
        """Simple code tokenization"""
        import re
        # Split on whitespace and common symbols
        tokens = re.findall(r'\w+|[^\w\s]', code)
        # Filter out very common tokens
        common_tokens = {'def', 'class', 'if', 'else', 'for', 'while', 'import', 'return'}
        return [token for token in tokens if token.lower() not in common_tokens]

    def _find_common_token_sequences(self, tokens1: list[str], tokens2: list[str]) -> list[str]:
        """Find common token sequences"""
        matcher = difflib.SequenceMatcher(None, tokens1, tokens2)
        common_sequences = []

        for match in matcher.get_matching_blocks():
            if match.size > 2:  # Only sequences of 3+ tokens
                sequence = ' '.join(tokens1[match.a:match.a + match.size])
                common_sequences.append(sequence)

        return common_sequences

    def _analyze_line_similarity(self, code1: str, code2: str) -> SimilarityMatch | None:
        """Analyze similarity based on code lines"""
        try:
            lines1 = [line.strip() for line in code1.split('\n') if line.strip()]
            lines2 = [line.strip() for line in code2.split('\n') if line.strip()]

            # Calculate line-based similarity
            matcher = difflib.SequenceMatcher(None, lines1, lines2)
            similarity = matcher.ratio()

            if similarity > 0.4:  # Only report significant line similarities
                common_lines = []
                for match in matcher.get_matching_blocks():
                    if match.size > 1:  # Sequences of 2+ lines
                        for i in range(match.size):
                            common_lines.append(lines1[match.a + i])

                return SimilarityMatch(
                    method=SimilarityMethod.LINE_BASED,
                    score=similarity,
                    confidence=0.6,
                    matched_sections={
                        "common_lines": common_lines[:5],  # First 5 common lines
                        "total_common_lines": len(common_lines)
                    },
                    explanation=f"Line similarity: {similarity:.2f} based on exact line matching"
                )

        except Exception as e:
            logger.error("Line similarity analysis failed", error=str(e))

        return None

    def _analyze_function_similarity(self, code1: str, code2: str) -> SimilarityMatch | None:
        """Analyze similarity based on function signatures and structure"""
        try:
            functions1 = self._extract_functions(code1)
            functions2 = self._extract_functions(code2)

            if not functions1 or not functions2:
                return None

            # Compare function signatures
            common_functions = []
            for func1 in functions1:
                for func2 in functions2:
                    similarity = self._compare_functions(func1, func2)
                    if similarity > 0.7:
                        common_functions.append({
                            'name1': func1['name'],
                            'name2': func2['name'],
                            'similarity': similarity
                        })

            if common_functions:
                avg_similarity = sum(f['similarity'] for f in common_functions) / len(common_functions)

                return SimilarityMatch(
                    method=SimilarityMethod.FUNCTION_SIGNATURE,
                    score=avg_similarity,
                    confidence=0.8,
                    matched_sections={
                        "common_functions": common_functions,
                        "total_functions": len(common_functions)
                    },
                    explanation=f"Function similarity: {avg_similarity:.2f} based on function structure"
                )

        except Exception as e:
            logger.error("Function similarity analysis failed", error=str(e))

        return None

    def _extract_functions(self, code: str) -> list[dict[str, Any]]:
        """Extract function information from code"""
        try:
            tree = ast.parse(code)
            functions = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'body_length': len(node.body),
                        'returns': any(isinstance(n, ast.Return) for n in ast.walk(node))
                    })

            return functions
        except SyntaxError:
            return []

    def _compare_functions(self, func1: dict[str, Any], func2: dict[str, Any]) -> float:
        """Compare two function signatures"""
        score = 0.0

        # Name similarity (less weight if names are obviously different)
        name_sim = difflib.SequenceMatcher(None, func1['name'], func2['name']).ratio()
        score += name_sim * 0.3

        # Argument similarity
        args1, args2 = set(func1['args']), set(func2['args'])
        arg_sim = len(args1.intersection(args2)) / max(len(args1), len(args2), 1)
        score += arg_sim * 0.4

        # Body length similarity
        len1, len2 = func1['body_length'], func2['body_length']
        len_sim = 1 - abs(len1 - len2) / max(len1, len2, 1)
        score += len_sim * 0.2

        # Return statement similarity
        ret_sim = 1.0 if func1['returns'] == func2['returns'] else 0.0
        score += ret_sim * 0.1

        return score

    def _calculate_overall_score(self, scores: dict[str, float]) -> float:
        """Calculate weighted overall similarity score"""
        if not scores:
            return 0.0

        weights = {
            'structural': 0.4,
            'token': 0.3,
            'line': 0.2,
            'function': 0.1
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for score_type, score in scores.items():
            weight = weights.get(score_type, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0


class SimilarityDetector:
    """Main similarity detection service"""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.python_analyzer = PythonSimilarityAnalyzer(threshold)

    def compare_submissions(
        self,
        submission1: dict[str, Any],
        submission2: dict[str, Any],
        methods: list[SimilarityMethod] | None = None
    ) -> SimilarityResult:
        """
        Compare two code submissions for similarity

        Args:
            submission1: First submission with 'code' and 'language'
            submission2: Second submission with 'code' and 'language'
            methods: Similarity methods to use

        Returns:
            SimilarityResult with similarity analysis
        """
        code1 = submission1.get('code', '')
        code2 = submission2.get('code', '')
        language = submission1.get('language', 'python').lower()

        if language == 'python':
            return self.python_analyzer.analyze_similarity(code1, code2, methods)
        else:
            logger.warning("Similarity analysis not implemented for language", language=language)
            return SimilarityResult(
                overall_score=0.0,
                matches=[],
                flagged=False,
                threshold_used=self.threshold,
                methods_used=methods or []
            )

    def batch_similarity_check(
        self,
        submissions: list[dict[str, Any]],
        methods: list[SimilarityMethod] | None = None
    ) -> list[tuple[int, int, SimilarityResult]]:
        """
        Perform pairwise similarity checks on a batch of submissions

        Args:
            submissions: List of submissions to compare
            methods: Similarity methods to use

        Returns:
            List of (index1, index2, SimilarityResult) for flagged pairs
        """
        results = []

        for i in range(len(submissions)):
            for j in range(i + 1, len(submissions)):
                similarity = self.compare_submissions(
                    submissions[i],
                    submissions[j],
                    methods
                )

                if similarity.flagged or similarity.overall_score > 0.3:  # Report moderate+ similarities
                    results.append((i, j, similarity))

        logger.info("Batch similarity check completed",
                   total_comparisons=len(submissions) * (len(submissions) - 1) // 2,
                   flagged_pairs=len(results))

        return results


# Global similarity detector instance
similarity_detector = SimilarityDetector()

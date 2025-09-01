"""
Similarity analysis service for detecting plagiarism across submissions
"""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from codelens.analyzers import SimilarityMethod, SimilarityResult, similarity_detector
from codelens.core.config import settings
from codelens.models import AnalysisReport
from codelens.models import SimilarityMatch as SimilarityMatchModel

logger = structlog.get_logger()


class SimilarityService:
    """Service for managing similarity analysis and plagiarism detection"""

    def __init__(self) -> None:
        self.detector = similarity_detector
        self.enabled = settings.similarity.enabled
        self.threshold = settings.similarity.threshold
        self.methods = [
            SimilarityMethod(method) for method in settings.similarity.methods
        ]

    async def check_submission_similarity(
        self,
        submission_code: str,
        submission_id: str,
        assignment_id: int,
        language: str,
        db: AsyncSession,
        student_id: str | None = None
    ) -> dict[str, Any]:
        """
        Check similarity of a new submission against existing submissions

        Args:
            submission_code: Code content to check
            submission_id: Unique submission identifier
            assignment_id: Assignment ID
            language: Programming language
            db: Database session
            student_id: Optional student ID to exclude from comparison

        Returns:
            Dictionary with similarity analysis results
        """
        if not self.enabled:
            logger.info("Similarity checking disabled")
            return {
                "enabled": False,
                "matches": [],
                "highest_similarity": 0.0,
                "flagged": False
            }

        try:
            # Get existing submissions for the same assignment
            query = select(AnalysisReport).where(
                and_(
                    AnalysisReport.assignment_id == assignment_id,
                    AnalysisReport.language == language.lower(),
                    AnalysisReport.submission_id != submission_id  # Exclude self
                )
            )

            # Exclude same student's previous submissions if student_id provided
            if student_id:
                query = query.where(AnalysisReport.student_id != student_id)

            result = await db.execute(query)
            existing_reports = result.scalars().all()

            logger.info("Checking similarity against existing submissions",
                       submission_id=submission_id,
                       existing_count=len(existing_reports))

            if not existing_reports:
                return {
                    "enabled": True,
                    "matches": [],
                    "highest_similarity": 0.0,
                    "flagged": False,
                    "comparison_count": 0
                }

            # Perform similarity checks
            similarity_matches = []
            highest_similarity = 0.0

            for report in existing_reports:
                # We don't store the original code, so we can't do real comparison
                # In a real implementation, you might:
                # 1. Store code hashes for quick comparison
                # 2. Store AST fingerprints
                # 3. Use external storage for code content
                # 4. Generate similarity scores from stored features

                # For now, simulate similarity checking
                simulated_similarity = self._simulate_similarity_check(
                    submission_code,
                    report.file_hash,  # Using hash as proxy
                    language
                )

                if simulated_similarity.overall_score > 0.3:  # Only store significant matches
                    similarity_matches.append({
                        "report_id": report.id,
                        "matched_submission_id": report.submission_id,
                        "student_id": report.student_id,
                        "similarity_score": simulated_similarity.overall_score,
                        "methods_used": [m.value for m in simulated_similarity.methods_used],
                        "flagged": simulated_similarity.flagged
                    })

                    highest_similarity = max(highest_similarity, simulated_similarity.overall_score)

                    # Store in database
                    await self._store_similarity_match(
                        db, submission_id, report, simulated_similarity
                    )

            # Check if flagged based on highest similarity
            flagged = highest_similarity >= self.threshold

            result_data = {
                "enabled": True,
                "matches": similarity_matches,
                "highest_similarity": highest_similarity,
                "flagged": flagged,
                "comparison_count": len(existing_reports),
                "threshold_used": self.threshold,
                "methods_used": [m.value for m in self.methods]
            }

            logger.info("Similarity check completed",
                       submission_id=submission_id,
                       matches_found=len(similarity_matches),
                       highest_similarity=highest_similarity,
                       flagged=flagged)

            return result_data

        except Exception as e:
            logger.error("Similarity check failed",
                        submission_id=submission_id,
                        error=str(e))
            return {
                "enabled": True,
                "matches": [],
                "highest_similarity": 0.0,
                "flagged": False,
                "error": f"Similarity check failed: {str(e)}"
            }

    async def batch_similarity_analysis(
        self,
        submissions: list[dict[str, Any]],
        assignment_id: int,
        db: AsyncSession
    ) -> list[dict[str, Any]]:
        """
        Perform batch similarity analysis on multiple submissions

        Args:
            submissions: List of submission dictionaries
            assignment_id: Assignment ID
            db: Database session

        Returns:
            List of similarity analysis results
        """
        if not self.enabled or len(submissions) < 2:
            return []

        try:
            logger.info("Starting batch similarity analysis",
                       assignment_id=assignment_id,
                       submission_count=len(submissions))

            # Perform pairwise comparisons
            flagged_pairs = self.detector.batch_similarity_check(
                submissions, self.methods
            )

            # Store results and prepare response
            batch_results = []

            for i, j, similarity_result in flagged_pairs:
                sub1, sub2 = submissions[i], submissions[j]

                result_data = {
                    "submission1_id": sub1.get("submission_id"),
                    "submission2_id": sub2.get("submission_id"),
                    "student1_id": sub1.get("student_id"),
                    "student2_id": sub2.get("student_id"),
                    "similarity_score": similarity_result.overall_score,
                    "flagged": similarity_result.flagged,
                    "methods_used": [m.value for m in similarity_result.methods_used],
                    "matches": [
                        {
                            "method": match.method.value,
                            "score": match.score,
                            "confidence": match.confidence,
                            "explanation": match.explanation
                        }
                        for match in similarity_result.matches
                    ]
                }

                batch_results.append(result_data)

                # Store in database if both submissions have IDs
                if sub1.get("report_id") and sub2.get("report_id"):
                    await self._store_batch_similarity_match(
                        db, sub1["report_id"], sub2["report_id"], similarity_result
                    )

            logger.info("Batch similarity analysis completed",
                       flagged_pairs=len(batch_results))

            return batch_results

        except Exception as e:
            logger.error("Batch similarity analysis failed", error=str(e))
            return []

    def _simulate_similarity_check(
        self,
        code: str,
        existing_hash: str,
        language: str
    ) -> SimilarityResult:
        """
        Simulate similarity checking (placeholder implementation)

        In a real implementation, this would:
        1. Retrieve the actual code content from storage
        2. Perform full similarity analysis
        3. Return detailed similarity results

        For now, we simulate based on simple heuristics
        """
        from codelens.utils import calculate_file_hash

        current_hash = calculate_file_hash(code)

        # Very simple simulation - in reality, you'd do full analysis
        if current_hash == existing_hash:
            # Identical files
            similarity_score = 1.0
        else:
            # Simulate some similarity based on hash similarity
            # This is just for demonstration - real implementation needed
            hash_similarity = len(set(current_hash).intersection(set(existing_hash))) / len(set(current_hash + existing_hash))
            similarity_score = hash_similarity * 0.3  # Scale down since hash similarity is not meaningful

        from codelens.analyzers.similarity_analyzer import (
            SimilarityMatch,
            SimilarityResult,
        )

        matches = []
        if similarity_score > 0.5:
            matches.append(SimilarityMatch(
                method=SimilarityMethod.TOKEN_BASED,
                score=similarity_score,
                confidence=0.6,
                matched_sections={"simulated": True},
                explanation=f"Simulated similarity: {similarity_score:.2f}"
            ))

        return SimilarityResult(
            overall_score=similarity_score,
            matches=matches,
            flagged=similarity_score >= self.threshold,
            threshold_used=self.threshold,
            methods_used=self.methods
        )

    async def _store_similarity_match(
        self,
        db: AsyncSession,
        submission_id: str,
        matched_report: Any,
        similarity_result: SimilarityResult
    ) -> None:
        """Store similarity match in database"""
        try:
            # Get report ID for current submission
            current_report_query = select(AnalysisReport).where(
                AnalysisReport.submission_id == submission_id
            )
            current_report_result = await db.execute(current_report_query)
            current_report = current_report_result.scalar_one_or_none()

            if not current_report:
                logger.warning("Could not find report for similarity storage",
                             submission_id=submission_id)
                return

            # Create similarity match record
            similarity_match = SimilarityMatchModel(
                report_id=current_report.id,
                matched_report_id=matched_report.id,
                similarity_score=similarity_result.overall_score,
                similarity_method="combined",  # Multiple methods combined
                matched_sections={
                    "methods": [m.method.value for m in similarity_result.matches],
                    "scores": {m.method.value: m.score for m in similarity_result.matches}
                },
                confidence=max([m.confidence for m in similarity_result.matches], default=0.5),
                flagged=similarity_result.flagged
            )

            db.add(similarity_match)
            await db.commit()

            logger.debug("Stored similarity match",
                        report_id=current_report.id,
                        matched_report_id=matched_report.id,
                        score=similarity_result.overall_score)

        except Exception as e:
            logger.error("Failed to store similarity match", error=str(e))
            await db.rollback()

    async def _store_batch_similarity_match(
        self,
        db: AsyncSession,
        report1_id: int,
        report2_id: int,
        similarity_result: SimilarityResult
    ) -> None:
        """Store batch similarity match in database"""
        try:
            # Create similarity match records (bidirectional)
            match1 = SimilarityMatchModel(
                report_id=report1_id,
                matched_report_id=report2_id,
                similarity_score=similarity_result.overall_score,
                similarity_method="batch_analysis",
                matched_sections={
                    "methods": [m.method.value for m in similarity_result.matches],
                    "batch_analysis": True
                },
                confidence=max([m.confidence for m in similarity_result.matches], default=0.7),
                flagged=similarity_result.flagged
            )

            match2 = SimilarityMatchModel(
                report_id=report2_id,
                matched_report_id=report1_id,
                similarity_score=similarity_result.overall_score,
                similarity_method="batch_analysis",
                matched_sections={
                    "methods": [m.method.value for m in similarity_result.matches],
                    "batch_analysis": True
                },
                confidence=max([m.confidence for m in similarity_result.matches], default=0.7),
                flagged=similarity_result.flagged
            )

            db.add(match1)
            db.add(match2)
            await db.commit()

        except Exception as e:
            logger.error("Failed to store batch similarity match", error=str(e))
            await db.rollback()

    async def get_submission_similarities(
        self,
        report_id: int,
        db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Get all similarity matches for a specific report"""
        try:
            query = select(SimilarityMatchModel).where(
                SimilarityMatchModel.report_id == report_id
            )
            result = await db.execute(query)
            matches = result.scalars().all()

            return [
                {
                    "id": match.id,
                    "matched_report_id": match.matched_report_id,
                    "similarity_score": match.similarity_score,
                    "similarity_method": match.similarity_method,
                    "confidence": match.confidence,
                    "flagged": match.flagged,
                    "reviewed": match.reviewed,
                    "detected_at": match.detected_at
                }
                for match in matches
            ]

        except Exception as e:
            logger.error("Failed to get submission similarities",
                        report_id=report_id, error=str(e))
            return []

    async def review_similarity_match(
        self,
        match_id: int,
        decision: str,
        reviewer_notes: str | None,
        db: AsyncSession
    ) -> bool:
        """Review and mark a similarity match"""
        try:
            query = select(SimilarityMatchModel).where(
                SimilarityMatchModel.id == match_id
            )
            result = await db.execute(query)
            match = result.scalar_one_or_none()

            if not match:
                return False

            match.reviewed = True
            match.review_decision = decision
            match.reviewer_notes = reviewer_notes
            match.reviewed_at = datetime.utcnow()

            await db.commit()

            logger.info("Similarity match reviewed",
                       match_id=match_id,
                       decision=decision)

            return True

        except Exception as e:
            logger.error("Failed to review similarity match",
                        match_id=match_id, error=str(e))
            await db.rollback()
            return False


# Global similarity service instance
similarity_service = SimilarityService()

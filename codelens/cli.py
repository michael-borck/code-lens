"""
Command-line interface for CodeLens batch processing
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import structlog

from codelens.core.config import settings
from codelens.services.batch_processor import BatchProcessingConfig, batch_processor
from codelens.utils import calculate_grade_letter, format_file_size

logger = structlog.get_logger()


async def process_directory_command(args: Any) -> int:
    """Process a directory of code submissions"""
    try:
        print(f"CodeLens Batch Processor v{settings.version}")
        print(f"Processing directory: {args.directory}")
        print("-" * 50)

        # Configure batch processor
        config = BatchProcessingConfig(
            parallel_processing=not args.sequential,
            max_concurrent=args.max_concurrent,
            skip_unsupported_files=not args.include_unsupported,
            extract_student_info=args.extract_student_info,
            default_language=args.language
        )

        # Override student ID patterns if provided
        if args.student_id_patterns:
            config.student_id_patterns = args.student_id_patterns.split(',')

        # Create batch processor with config
        processor = batch_processor.__class__(config)

        # Process directory
        result = await processor.process_directory(
            directory_path=args.directory,
            assignment_id=args.assignment_id,
            rubric_id=args.rubric_id,
            language=args.language
        )

        # Display results
        print("\n" + "=" * 60)
        print("BATCH PROCESSING RESULTS")
        print("=" * 60)

        print(f"Batch ID: {result.batch_id}")
        print(f"Total Files: {result.total_files}")
        print(f"Processed: {result.processed_files}")
        print(f"Failed: {result.failed_files}")
        print(f"Success Rate: {(result.processed_files / result.total_files * 100):.1f}%" if result.total_files > 0 else "0%")
        print(f"Processing Time: {result.processing_time:.2f} seconds")

        if result.average_score is not None:
            print(f"Average Score: {result.average_score:.1f}%")
            print(f"Average Grade: {calculate_grade_letter(result.average_score)}")

        # Score distribution
        if result.score_distribution:
            print("\nScore Distribution:")
            for grade_range, count in result.score_distribution.items():
                percentage = (count / result.processed_files * 100) if result.processed_files > 0 else 0
                print(f"  {grade_range}: {count} students ({percentage:.1f}%)")

        # Errors
        if result.errors:
            print("\nErrors:")
            for i, error in enumerate(result.errors[:10], 1):  # Show first 10 errors
                print(f"  {i}. {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")

        # Detailed results
        if args.detailed and result.results:
            print("\n" + "-" * 60)
            print("DETAILED RESULTS")
            print("-" * 60)

            for i, res in enumerate(result.results[:args.max_details], 1):
                print(f"\n{i}. Submission: {res.submission_id}")
                print(f"   Success: {res.success}")
                if res.total_score is not None:
                    print(f"   Score: {res.total_score:.1f}% ({calculate_grade_letter(res.total_score)})")
                print(f"   Issues: {len(res.issues)}")
                if res.metrics:
                    print(f"   LOC: {res.metrics.lines_of_code}")
                    print(f"   Complexity: {res.metrics.cyclomatic_complexity}")
                if res.error_message:
                    print(f"   Error: {res.error_message}")

        # Save results to file if requested
        if args.output:
            output_data = {
                "batch_id": result.batch_id,
                "summary": {
                    "total_files": result.total_files,
                    "processed_files": result.processed_files,
                    "failed_files": result.failed_files,
                    "processing_time": result.processing_time,
                    "average_score": result.average_score,
                    "score_distribution": result.score_distribution
                },
                "results": [
                    {
                        "submission_id": r.submission_id,
                        "success": r.success,
                        "total_score": r.total_score,
                        "issues_count": len(r.issues),
                        "metrics": r.metrics.dict() if r.metrics else None,
                        "error_message": r.error_message
                    }
                    for r in result.results
                ],
                "errors": result.errors
            }

            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)

            print(f"\nResults saved to: {args.output}")

        return 0 if result.success else 1

    except Exception as e:
        logger.error("Directory processing failed", error=str(e))
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


async def analyze_single_file(args: Any) -> int:
    """Analyze a single code file"""
    try:
        file_path = Path(args.file)

        if not file_path.exists():
            print(f"Error: File {args.file} does not exist", file=sys.stderr)
            return 1

        print(f"Analyzing file: {file_path}")
        print(f"File size: {format_file_size(file_path.stat().st_size)}")
        print("-" * 40)

        # Read file content
        with open(file_path, encoding='utf-8') as f:
            code = f.read()

        # Process as single file batch
        files_data = [{
            "code": code,
            "path": str(file_path),
            "student_id": args.student_id,
            "student_name": args.student_name
        }]

        result = await batch_processor.process_files_list(
            files_data=files_data,
            assignment_id=args.assignment_id,
            rubric_id=args.rubric_id,
            language=args.language
        )

        if result.results:
            res = result.results[0]
            print(f"Analysis completed in {result.processing_time:.2f} seconds")
            print(f"Success: {res.success}")

            if res.total_score is not None:
                print(f"Score: {res.total_score:.1f}% ({calculate_grade_letter(res.total_score)})")

            if res.metrics:
                print("\nCode Metrics:")
                print(f"  Lines of Code: {res.metrics.lines_of_code}")
                print(f"  Cyclomatic Complexity: {res.metrics.cyclomatic_complexity}")
                print(f"  Functions: {res.metrics.function_count}")
                print(f"  Classes: {res.metrics.class_count}")

            if res.issues:
                print(f"\nIssues Found ({len(res.issues)}):")
                for i, issue in enumerate(res.issues[:10], 1):  # Show first 10 issues
                    print(f"  {i}. Line {issue.line}: {issue.message} ({issue.severity.value})")
                if len(res.issues) > 10:
                    print(f"  ... and {len(res.issues) - 10} more issues")

            if res.error_message:
                print(f"\nError: {res.error_message}")

        return 0 if result.success else 1

    except Exception as e:
        logger.error("File analysis failed", error=str(e))
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="CodeLens - Automated Code Analysis for Educational Use",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a directory of Python submissions
  python -m codelens.cli batch /path/to/submissions --language python

  # Process with specific rubric and assignment
  python -m codelens.cli batch /path/to/submissions --rubric-id 1 --assignment-id 5

  # Analyze a single file
  python -m codelens.cli analyze submission.py --student-id cs123456

  # Generate detailed report with output file
  python -m codelens.cli batch /submissions --detailed --output results.json
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Batch processing command
    batch_parser = subparsers.add_parser('batch', help='Process directory of code submissions')
    batch_parser.add_argument('directory', help='Directory containing code submissions')
    batch_parser.add_argument('--language', default='python',
                            help='Programming language (default: python)')
    batch_parser.add_argument('--assignment-id', type=int,
                            help='Assignment ID for database storage')
    batch_parser.add_argument('--rubric-id', type=int,
                            help='Rubric ID for grading')
    batch_parser.add_argument('--sequential', action='store_true',
                            help='Process files sequentially instead of parallel')
    batch_parser.add_argument('--max-concurrent', type=int, default=5,
                            help='Maximum concurrent processing (default: 5)')
    batch_parser.add_argument('--include-unsupported', action='store_true',
                            help='Include unsupported file types')
    batch_parser.add_argument('--no-extract-student-info', dest='extract_student_info',
                            action='store_false', default=True,
                            help='Disable automatic student info extraction')
    batch_parser.add_argument('--student-id-patterns',
                            help='Comma-separated regex patterns for student ID extraction')
    batch_parser.add_argument('--detailed', action='store_true',
                            help='Show detailed results for each submission')
    batch_parser.add_argument('--max-details', type=int, default=20,
                            help='Maximum detailed results to show (default: 20)')
    batch_parser.add_argument('--output', '-o',
                            help='Output file for results (JSON format)')

    # Single file analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single code file')
    analyze_parser.add_argument('file', help='Code file to analyze')
    analyze_parser.add_argument('--language', default='python',
                              help='Programming language (default: python)')
    analyze_parser.add_argument('--student-id', help='Student ID')
    analyze_parser.add_argument('--student-name', help='Student name')
    analyze_parser.add_argument('--assignment-id', type=int,
                              help='Assignment ID for database storage')
    analyze_parser.add_argument('--rubric-id', type=int,
                              help='Rubric ID for grading')

    return parser


async def main() -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'batch':
        return await process_directory_command(args)
    elif args.command == 'analyze':
        return await analyze_single_file(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)

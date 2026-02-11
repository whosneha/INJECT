import argparse
from src.inject import inject_cluster
from src.detection_test import run_detection_pipeline
from src.completeness import compute_completeness_curve
from src.io import save_catalog, load_results

def main():
    parser = argparse.ArgumentParser(description="Star Cluster Injection Pipeline")
    
    subparsers = parser.add_subparsers(dest='command')

    # Subparser for injecting clusters
    inject_parser = subparsers.add_parser('inject', help='Inject artificial star clusters into images')
    inject_parser.add_argument('--image', required=True, help='Path to the image file')
    inject_parser.add_argument('--output', required=True, help='Output path for the injected catalog')
    inject_parser.add_argument('--params', required=True, help='Parameters for the cluster injection')

    # Subparser for running detection tests
    detect_parser = subparsers.add_parser('detect', help='Run detection pipeline on images with injected clusters')
    detect_parser.add_argument('--image', required=True, help='Path to the image file with injected clusters')
    detect_parser.add_argument('--output', required=True, help='Output path for detection results')

    # Subparser for computing completeness
    completeness_parser = subparsers.add_parser('completeness', help='Compute completeness curves')
    completeness_parser.add_argument('--catalog', required=True, help='Path to the injected catalog')
    completeness_parser.add_argument('--output', required=True, help='Output path for completeness results')

    args = parser.parse_args()

    if args.command == 'inject':
        inject_cluster(args.image, args.output, args.params)
    elif args.command == 'detect':
        run_detection_pipeline(args.image, args.output)
    elif args.command == 'completeness':
        compute_completeness_curve(args.catalog, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
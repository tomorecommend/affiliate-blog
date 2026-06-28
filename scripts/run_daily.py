import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="アフィリエイトブログの日次記事生成バッチ")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API呼び出しまでは実行するが、ファイル書き込み・履歴更新は行わない",
    )
    args = parser.parse_args()

    result = run(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

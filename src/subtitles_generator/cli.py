import argparse


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Make subtitles for a video in its own language and others.")
    parser.add_argument("input", help="path to the video")
    parser.parse_args(argv)
    raise SystemExit("Not implemented yet")

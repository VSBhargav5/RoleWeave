"""Isolate retired Tk test lifecycles in CI; never enable native windows locally."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
TESTS=ROOT/'tests'


def cases(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from cases(item)
        else:yield item


def main():
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(TESTS))
    if sys.argv[1:2]==['--list-only']:
        run=False
    else:
        run=True
        if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('ROLEWEAVE_TEST_NATIVE_ARCHIVE')!='1':
            raise SystemExit('Native archive execution is restricted to isolated Windows CI')
    if sys.argv[1:2]==['--case']:
        if len(sys.argv)!=3:raise SystemExit('Choose exactly one archived test case')
        suite=unittest.defaultTestLoader.loadTestsFromName(sys.argv[2]);result=unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(not result.wasSuccessful())
    modules={path.stem for path in TESTS.glob('test_*.py') if 'ROLEWEAVE_TEST_NATIVE_ARCHIVE' in path.read_text(encoding='utf-8')}
    suite=unittest.defaultTestLoader.discover(str(TESTS))
    identifiers=[case.id() for case in cases(suite) if case.__class__.__module__ in modules]
    if not identifiers:raise SystemExit('Native archive discovery unexpectedly returned no tests')
    for identifier in identifiers:
        if run:subprocess.run([sys.executable,str(Path(__file__).resolve()),'--case',identifier],cwd=ROOT,check=True)
        else:print(identifier)
    print(str(len(identifiers))+' isolated archived test cases'+(' passed' if run else ' listed; no test executed'))


if __name__=='__main__':main()

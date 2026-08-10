#!/usr/bin/env python3
"""Table test for the audit's own patterns.

An audit is code, and this one has already produced three classes of false positive in a
day. A check that over-reports gets ignored; a check that is quietly broken reports nothing
and looks like good news. Both failures are invisible without a table like this.
"""
import re, sys
sys.path.insert(0, "studio/_tools")
import audit

STDERR = [p for p, w in audit.SILENT if "STDERR" in w][0]

CASES = [
    # The real bug: a filter that reports on stderr, silenced.
    (True,  'run(["ffmpeg", "-v", "error", "-i", p, "-af", "silencedetect=n=-32dB"])'),
    (True,  'sh("ffmpeg", "-v", "error", "-i", f, "-af", "volumedetect", "-f", "null")'),
    # Not bugs: these report on stdout or to a file, and -v error is correct for them.
    (False, 'sh("ffmpeg", "-v", "error", "-i", p, "-vf", "metadata=print:key=X:file=%s" % t)'),
    (False, 'run(["ffprobe", "-v", "error", "-show_entries", "format=duration"])'),
    (False, 'sh("ffmpeg", "-v", "error", "-i", p, "-f", "md5", "-")'),
]

bad = 0
for want, src in CASES:
    got = bool(re.search(STDERR, src, re.S))
    ok = got == want
    bad += not ok
    print("  %-4s want %-5s got %-5s %s" % ("ok" if ok else "FAIL", want, got, src[:60]))
print("\n  %d wrong of %d" % (bad, len(CASES)))
sys.exit(1 if bad else 0)

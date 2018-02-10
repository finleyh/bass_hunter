# Copyright (C) 2011-2013 Claudio Guarnieri.
# Copyright (C) 2014-2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

GITHUB_URL = "https://github.com/"
ISSUES_PAGE_URL = "https://github.com/finleyh/bass_hunter/issues"
DOCS_URL = "https://github.com/finleyh/bass_hunter/wiki"
BASS_HUNTER_ROOT="/opt/bass_hunter/"
API_PATH="/api/v1/"

def faq(entry):
    return "%s/faq/index.html#%s" % (DOCS_URL, entry)

#!/usr/bin/python

import sys

content = """
<root>
    <id>lgfrbcsgo.async</id>
    <version>{version}</version>
    <name>Async</name>
    <description>Library for asynchronous programming inside of WoT mods.</description>
</root>
"""

print(content.format(version=sys.argv[1]))

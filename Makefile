VERSION = $(shell git describe --tags | sed "s/^v//")
WOTMOD_NAME = lgfrbcsgo.async_$(VERSION).wotmod

clean-build:
	rm -rf build
	mkdir -p build

clean-dist:
	rm -rf dist
	mkdir -p dist/unpacked

copy-python-source: clean-build
	cp -r mod_async build

compile: copy-python-source
	python2.7 -m compileall build

copy-wotmod-content: compile clean-dist
	cp LICENSE dist/unpacked
	cp README.md dist/unpacked

	mkdir -p dist/unpacked/res/scripts/client
	cp -r build/* dist/unpacked/res/scripts/client

wotmod: copy-wotmod-content
	./scripts/template_meta_xml.py $(VERSION) > dist/unpacked/meta.xml
	cd dist/unpacked; 7z a -mx=0 -tzip ../$(WOTMOD_NAME) .

gh-actions-wotmod: wotmod
	echo "::set-output name=version::$(VERSION)"
	echo "::set-output name=wotmod_name::$(WOTMOD_NAME)"

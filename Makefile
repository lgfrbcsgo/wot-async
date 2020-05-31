clean-build:
	rm -rf build
	mkdir -p build

clean-dist:
	rm -rf dist
	mkdir -p dist

copy-python-source: clean-build
	cp -r mod_async build

compile: copy-python-source
	python2.7 -m compileall build

copy-wotmod-content: compile clean-dist
	mkdir -p dist/unpacked
	cp LICENSE dist/unpacked
	cp README.md dist/unpacked

	mkdir -p dist/unpacked/res/scripts/client
	cp -r build/* dist/unpacked/res/scripts/client

wotmod: copy-wotmod-content
	cd dist/unpacked; zip -0r ../lgfrbcsgo.async_$(shell git tag | sed "s/^v//").wotmod .

.PHONY: build-ui dev-ui install-ui

install-ui:
	cd frontend && npm install

dev-ui:
	cd frontend && npm run dev

build-ui:
	cd frontend && npm run build

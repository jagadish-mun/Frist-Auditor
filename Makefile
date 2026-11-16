.PHONY: demo end-demo demo-status demo-classic demo-gate test validate

demo:
	./scripts/demo.sh

end-demo:
	@.venv/bin/python gen/active.py end

demo-status:
	@.venv/bin/python gen/active.py status

demo-classic:
	./scripts/demo_classic.sh

demo-gate:
	.venv/bin/python gen/gate.py

test:
	.venv/bin/python -m pytest -q tests/

validate:
	.venv/bin/python validate.py && .venv/bin/python validate.py --heldout && .venv/bin/python validate.py --draft

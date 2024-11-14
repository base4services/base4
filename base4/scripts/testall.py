import os


def do():
	os.system(
		'''
	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

	if [[ "$SCRIPT_DIR" == *"/.venv/"* ]]; then
	    cd "$SCRIPT_DIR/../../src/.."
	    pwd
	else
	    cd "$SCRIPT_DIR/../.."
	    pwd
	fi

	TEST_DATABASE=sqlite pytest -n 8 --disable-warnings tests --no-cov
	cd -
	'''
	)


if __name__ == '__main__':
	do()

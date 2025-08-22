Steps:
```
source venv/bin/activate
pip install -r requirements.txt
pip install -e .  # install project to dev env
python test_build.py
# Build without --site-packages to use existing venv packages instead of bundling them
shiv --compressed --compile-pyc --python "/usr/bin/python3" --output-file main_sicbo_light.pyz --entry-point main_sicbo:main .
python main_sicbo.pyz
```
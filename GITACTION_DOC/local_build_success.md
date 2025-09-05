Steps:
```
source venv/bin/activate
pip install -r requirements.txt
pip install -e .  # install project to dev env
python test_build.py
shiv --compressed --compile-pyc --site-packages . --python "/usr/bin/python3" --output-file main_sicbo.pyz --entry-point main_sicbo:main .
python main_sicbo.pyz
```
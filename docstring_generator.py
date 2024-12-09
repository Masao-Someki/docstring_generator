import argparse
import os
import glob
import ast
import re

from llm import ChatGPT


LLM = ChatGPT()


def top_level_functions(body):
    return (f for f in body
        if isinstance(f, ast.FunctionDef)
        and not f.name.startswith("_")
    )


def top_level_classes(body):
    return (f for f in body if isinstance(f, ast.ClassDef))


def get_indent(lines):
    # We extract the right indent level from the first line that includes non-space char.
    first_line = next((line for line in lines if line.strip()), "")
    return " " * (len(first_line) - len(first_line.lstrip()))


def format_docstring(docstring):
    indent = len(docstring) \
        - len(docstring.replace("\n","").lstrip()) \
        - len(docstring.split('\n')) + 1
    docstring = re.sub("^(\s{" + str(indent) + "})", "", docstring, flags=re.MULTILINE)
    return docstring


def update_with_llm(source_code, name, package):
    output = LLM(f"""Please generate a docstring for the {name}, which is part of the {package} package.
Include only docstrings, and do not include anything else.
If there is already a docstring, update it accordingly.

**Entire Python code**

```python
{source_code}
```

**Docstring**
""")
    docstring = re.compile(r'"""(.*?)"""', re.DOTALL).findall(output)[0]
    return docstring


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A simple command-line tool to convert temperatures.')
    parser.add_argument("--process_dirs", action="append", help="Path to the directory containing processed files.")
    args = parser.parse_args()

    for process_dir in args.process_dirs:
        print(f"Processing files from directory: {process_dir}")

        # 1. list all python files inside the directory recursively
        python_files = glob.glob(f"{process_dir}/**/*.py", recursive=True)

        total_file_count = len(python_files)

        for i_file, python_file in enumerate(python_files):
            if "__init__.py" in python_file:
                continue

            changes = [] # (start_lineno, end_lineno, content)
            # 2. Process function first and then class docstrings.
            # 2.1 load the python file
            print(f"Processing {python_file} ({i_file+1}/{total_file_count})", end='\r')
            with open(python_file, 'r') as file:
                source_code = file.read()
            
            # 2.2 parse the python file into an ast
            try:
                tree = ast.parse(source_code)
            except SyntaxError as e:
                print(f"Error parsing {python_file}: {e}")
                continue
            
            # 2.3 find all top-level functions and process function docstrings
            for function in list(top_level_functions(tree.body)):
                if function.name.startswith("_"):
                    continue

                # 2.4.1 Check if there is a docstring and insert it if not
                if not isinstance(function.body[0], ast.Expr):
                    ds = ast.Expr(
                        value=ast.Constant(""),
                        lineno=function.lineno+1,
                        end_lineno=function.lineno,
                    )
                    function.body.insert(0, ds)

                # 2.4.2 update the docstring with LLM
                updated_docstring = update_with_llm(source_code, function.name, python_file)
                changes.append((
                    function.body[0].lineno-1,
                    function.body[0].end_lineno,
                    updated_docstring
                ))
            
            # 2.4 find all top-level classes and process class docstrings
            for class_def in list(top_level_classes(tree.body)):
                print(f"Processing: {class_def.name} in {python_file} " \
                    + f"({i_file+1}/{total_file_count})", end='\r')
                
                # 2.4.1 Check if there is a docstring and insert it if not
                if not isinstance(class_def.body[0], ast.Expr):
                    ds = ast.Expr(
                        value=ast.Constant(""),
                        lineno=class_def.lineno+1,
                        end_lineno=class_def.lineno,
                    )
                    class_def.body.insert(0, ds)

                # 2.4.2 update the docstring with LLM
                updated_docstring = update_with_llm(source_code, class_def.name, python_file)
                changes.append((
                    class_def.body[0].lineno-1,
                    class_def.body[0].end_lineno,
                    updated_docstring
                ))

                # 2.4.3 find all methods in the class and process method docstrings
                for method in class_def.body[1:]:
                    if isinstance(method, ast.FunctionDef) and not method.name.startswith("_"):
                        
                        # 2.4.3.1 Check if there is a docstring and insert it if not
                        if not isinstance(method.body[0], ast.Expr):
                            ds = ast.Expr(
                                value=ast.Constant(""),
                                lineno=method.lineno+1,
                                end_lineno=method.lineno,
                            )
                            method.body.insert(0, ds)
                        
                        # 2.4.3.2 update the docstring with LLM
                        updated_docstring = update_with_llm(source_code, method.name, class_def.name)
                        changes.append((
                            method.body[0].lineno-1,
                            method.body[0].end_lineno,
                            updated_docstring
                        ))
            
            # 2.5 sort changes by start line number in deceasing order
            changes.sort(key=lambda x: x[0], reverse=True)
            
            # 2.6 split source code into lines
            lines = source_code.split('\n')
            
            # 2.7 insert updated docstrings into the source code 
            for change in changes:
                indent = get_indent(lines[change[1]:])
                changed_lines = change[2].split('\n')
                docstring = '\n'.join([f'{line}' for line in changed_lines]).strip()
                lines = lines[:change[0]] \
                    + [f'{indent}"""'] \
                    + [f'{indent}' + docstring] \
                    + [f'{indent}"""'] \
                    + lines[change[1]:]
            
            # 2.8 write the updated source code back to the file
            with open(python_file, 'w') as file:
                file.write('\n'.join(lines))
            
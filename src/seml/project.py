from pathlib import Path
from typing import Union


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def init_project(
    directory: Union[str, Path] = '.',
    template: str = 'default',
    yes: bool = False,
):
    """
    Initialize a new project in the given directory.

    Args:
        directory (Optional[Union[str, Path]], optional): The directory to initialize the project in. Defaults to '.'.
        template (str, optional): The template to use. Defaults to 'default'.
        yes (bool, optional): Whether to skip the confirmation prompt. Defaults to False.
    """
    import importlib.resources
    from click import prompt

    if directory is None:
        directory = Path()
    directory = Path(directory).absolute()
    # Ensure that the directory exists
    if not directory.exists():
        directory.mkdir(parents=True)

    # Ensure that its state is okay
    if any(directory.glob('**/*')) and not yes:
        if not prompt(
            f'Directory "{directory}" is not empty. Are you sure you want to initialize a new project here? (y/n)'
        ):
            exit(1)

    template_path = (
        importlib.resources.files('seml') / 'templates' / 'project' / template
    )
    template_path = Path(template_path)
    format_map = SafeDict(project_name=directory.name)

    # Copy files one-by-one
    for src in template_path.glob('**/*'):
        file_name = src.relative_to(template_path)
        target_file_name = Path(str(file_name).format_map(format_map))
        dst = directory / target_file_name
        # Create directories
        if src.is_dir():
            if not dst.exists():
                dst.mkdir()
        elif not dst.exists():
            # For templates fill in variables
            if src.suffixes[-1] == '.template':
                dst = dst.with_suffix(src.suffix.removesuffix('.template'))
                dst.write_text(src.read_text().format_map(format_map))
            else:
                # Other files copy directly
                dst.write_bytes(src.read_bytes())
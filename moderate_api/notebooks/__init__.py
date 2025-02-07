import types
from typing import Dict

from moderate_api.enums import Notebooks

from .exploration import notebook as exploration_notebook
from .synthethic_load import notebook as synthethic_load_notebook

ALL_NOTEBOOKS: Dict[Notebooks, types.ModuleType] = {
    Notebooks.EXPLORATION: exploration_notebook,
    Notebooks.SYNTHETIC_LOAD: synthethic_load_notebook,
}

from typing import List, Optional, Dict, Union
import logging

from seml.database import (build_filter_dict, get_collection)
from seml.errors import MongoDBError
from seml.settings import SETTINGS
from seml.typer import prompt

States = SETTINGS.STATES

def collection_set_description(
    db_collection_name: str,
    description: str,
    sacred_id: Optional[int] = None,
    filter_states: Union[Optional[List[str]], str] = None,
    filter_dict: Optional[Dict] = None,
    batch_id: Optional[int] = None,
    yes: bool = False):
    """ Sets (or updates) the description of experiment(s). 
    
    Parameters
    ----------
    db_collection_name : str
        Name of the collection to delete descriptions from
    description : str
        The description to set.
    sacred_id : Optional[int], optional
        If given, the id of the experiment to delete the descriptino of. Overrides other filters, by default None
    filter_states : Union[Optional[List[str]], str], optional
        Filter on experiment states, by default None
    filter_dict : Optional[Dict], optional
        Additional filters, by default None
    batch_id : Optional[int], optional
        Filter on the batch ID of experiments, by default None
    yes : bool, optional
        Whether to override confirmation prompts, by default False
    """
    from pymongo import UpdateOne
    
    collection = get_collection(db_collection_name)
    if sacred_id is None:
        if isinstance(filter_states, str):
            filter_states = [filter_states]
        filter_dict = build_filter_dict(filter_states, batch_id, filter_dict)
        exps = [exp for exp in collection.find(filter_dict, {'seml.description' : 1, 'config' : 1})]
        descriptions = [resolve_description(description, exp.get('config', {})) for exp in exps]
        num_to_overwrite = len([exp for exp, description in zip(exps, descriptions) if exp.get('seml', {}).get('description', None) is not None and \
            exp.get('seml', {}).get('description', None) != description])
        if not yes and num_to_overwrite >= SETTINGS.CONFIRM_UPDATE_DESCRIPTION_THRESHOLD and \
            not prompt(f"{num_to_overwrite} experiment(s) have a different description. Proceed?", type=bool):
            exit(1)
        result = collection.bulk_write([
            UpdateOne({'_id' : exp['_id']}, {'$set' : {'seml.description' : description}})
            for exp, description in zip(exps, descriptions)
        ])
    else:
        exp = collection.find_one({'_id': sacred_id}, {'seml.description' : 1, 'config' : 1})
        if exp is None:
            raise MongoDBError(f"No experiment found with ID {sacred_id}.")
        description = resolve_description(description, exp.get('config', {}))
        if not yes and exp.get('seml', {}).get('description', None) is not None and exp.get('seml', {}).get('description', None) != description and \
            SETTINGS.CONFIRM_UPDATE_DESCRIPTION_THRESHOLD <= 1 and \
            not prompt(f'Experiment with ID {sacred_id} has a different description ("{exp.get("seml", {}).get("description", None)}")'\
                '. Do you want to overwrite it?', type=bool):
            exit(1)
        result = collection.update_one({'_id': sacred_id}, {'$set' : {'seml.description' : description}})
    logging.info(f'Updated the descriptions of {result.modified_count} experiments.')
    
def collection_delete_description(
    db_collection_name: str,
    sacred_id: Optional[int] = None,
    filter_states: Union[Optional[List[str]], str] = None,
    filter_dict: Optional[Dict] = None,
    batch_id: Optional[int] = None,
    yes: bool = False):
    """Deletes the description of experiments

    Parameters
    ----------
    db_collection_name : str
        Name of the collection to delete descriptions from
    sacred_id : Optional[int], optional
        If given, the id of the experiment to delete the descriptino of. Overrides other filters, by default None
    filter_states : Union[Optional[List[str]], str], optional
        Filter on experiment states, by default None
    filter_dict : Optional[Dict], optional
        Additional filters, by default None
    batch_id : Optional[int], optional
        Filter on the batch ID of experiments, by default None
    yes : bool, optional
        Whether to override confirmation prompts, by default False
    """
    collection = get_collection(db_collection_name)
    update = {'$unset' : {'seml.description' : ''}}
    if sacred_id is None:
        if isinstance(filter_states, str):
            filter_states = [filter_states]
        filter_dict = build_filter_dict(filter_states, batch_id, filter_dict)
        exps = [exp for exp in collection.find(filter_dict, {'seml.description' : 1})
                if exp.get('seml', {}).get('description', None) is not None]
        if not yes and len(exps) >= SETTINGS.CONFIRM_DELETE_DESCRIPTION_THRESHOLD and \
            not prompt(f"Deleting descriptions of {len(exps)} experiment(s). Proceed?", type=bool):
            exit(1)
        result = collection.update_many(filter_dict, update)
    else:
        exp = collection.find_one({'_id': sacred_id}, {'seml.description' : 1})
        if exp is None:
            raise MongoDBError(f"No experiment found with ID {sacred_id}.")
        if not yes and exp.get('seml', {}).get('description', None) is not None and \
            SETTINGS.CONFIRM_DELETE_DESCRIPTION_THRESHOLD <= 1 and \
            not prompt(f'Deleting the description of experiment with ID {sacred_id} ("{exp.get("seml", {}).get("description", None)}")?', type=bool):
            exit(1)
        result = collection.update_one({'_id': sacred_id}, update)
    logging.info(f'Deleted the descriptions of {result.modified_count} experiments.')
    
def resolve_description(description: str, config: Dict) -> str:
    """ Resolves descriptions in an OmegaConf-like syntax.
    
    Example: `${data.name}` will resolve to the corresponding (nested) field in the config.

    Parameters
    ----------
    description : str
        The description to resolve
    config : Dict
        The configuration from which to resolve

    Returns
    -------
    str
        The resolved description
    """
    # TODO: Maybe use OmegaConf for seml altogether
    import re
    for match in re.findall(r'\$\{.*\}', description):
        value = config
        for key in match[2:-1].split('.'):
            try:
                value = value[key]
            except:
                logging.error(f'Could not access config value {match[2:-1]}')
                exit(1)
        description = description.replace(match, str(value))
    return description
        
        
        
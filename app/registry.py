from typing import get_args
from provider import Provider, ProviderBuilder
from audio import *
from trackinfo import *
from os.path import dirname, basename, isfile, join
import glob
from importlib import import_module

# Import all providers classes in providers folder
modules = glob.glob(join(dirname(__file__), "providers", "*.py"))
for module in [ "providers." + basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]:
    import_module(module)


class ProviderDescription[T : Provider]:

    def __init__(self, name: str, provider : T|Exception) -> None:

        self._provider = None
        self._name = name.removesuffix('Provider').capitalize()

        if type(provider) == Exception:
            self._exception = provider
        else:
            self._provider = provider

    @property
    def loaded_successfully(self) -> bool:
        return self._provider != None
    
    @property
    def name(self) -> str:
        return self._name

    @property
    def provider(self) -> T:
        return self._provider # type: ignore

    @property
    def loading_error(self) -> Exception:
        return self._exception


class ProviderRegistry:

    __registry : dict[type, ProviderDescription] = dict()

    def __init__(self, configuration : dict) -> None:
        self.configuration = configuration

    def load_providers(self):

        # Get all providers available from classes
        for builder_type in ProviderBuilder.__subclasses__():

            provider_type, configuration_type = get_args(builder_type.__orig_bases__[0]) # type: ignore
            key = configuration_type.__name__.lower().removesuffix('configuration')

            try:

                # If we got configuration set for this provider, instanciate
                if not (key in self.configuration):
                    raise Exception(f"Not loading {provider_type}, '{key}' is not defined in configuration")

                conf = configuration_type(**self.configuration[key])
                self.__registry[provider_type] = ProviderDescription(provider_type.__name__, builder_type().build(conf))

            except Exception as ex:
                self.__registry[provider_type] = ProviderDescription(provider_type.__name__, ex)
        

    def get_loaded_providers(self) -> list[Provider]:
        return [p.provider for p in self.__registry.values() if p.loaded_successfully]
    
    def get_providers(self) -> list[ProviderDescription]:
        return [p for p in self.__registry.values()]
    
    def get[T : Provider](self) -> Provider|None:        
        return self.__registry[type(T)].provider if (type(T) in self.__registry.keys() and self.__registry[type(T)].loaded_successfully) else None
        
    def get_by_name(self, name : str) -> Provider|None:
        for value in self.__registry.values():
            if value.loaded_successfully and value.provider.get_name() == name:
                return value.provider
            
        return None

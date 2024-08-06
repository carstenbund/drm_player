#!/usr/bin/python3

import configparser
from functools import wraps

class GenerativeBase(object):
    def _generate(self):
        s = self.__class__.__new__(self.__class__)
        s.__dict__ = self.__dict__.copy()
        return s

def _generative(func):
    @wraps(func)
    def decorator(self, *args, **kw):
        new_self = self._generate()
        func(new_self, *args, **kw)
        return new_self
    return decorator

class Config(GenerativeBase):
    def __init__(self, name=None):
        self.name = name
        self.data = {}

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        if key in ['name', 'data']:
            super().__setattr__(key, value)
        else:
            self.set(key, value)

    def __repr__(self):
        return repr(self.data)

    def __iter__(self):
        return iter(self.data.items())

    def __call__(self, key='name'):
        return self.get(key)

    def copy(self):
        clone = self._generate()
        return clone

    def save(self, filename='config.ini'):
        with open(filename, 'w') as sf:
            if self.name:
                sf.write(f'[{self.name}]\n')
            for key, value in self.data.items():
                value = str(value).replace(' ', '_')
                sf.write(f'{key} = {value}\n')
            sf.write('\n')

class ConfigLoader(Config):
    def __init__(self, filename='config.ini'):
        super().__init__()
        self.filename = filename
        self.load_config(filename)

    def load_config(self, filename):
        parser = configparser.ConfigParser()
        parser.read(filename)
        for section in parser.sections():
            config = Config(name=section)
            for key, value in parser[section].items():
                if value.isdigit():
                    value = int(value)
                elif value.lower() in ['true', 'false']:
                    value = parser.getboolean(section, key)
                config.set(key, value)
            #self.configs[section] = config
            #print(config)
            self.data[section] = config

    def get_config(self, section):
        return self.data.get(section)

    def set_config(self, section, key, value):
        if section not in self.data:
            self.data[section] = Config(name=section)
        self.data[section].set(key, value)

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        with open(filename, 'w') as sf:
            for section, config in self.data.items():
                if isinstance(config, Config):
                    sf.write(f'[{section}]\n')
                    for key, value in config.data.items():
                        value = str(value).replace(' ', '_')
                        sf.write(f'{key} = {value}\n')
                    sf.write('\n')
                else:
                    value = str(config).replace(' ', '_')
                    sf.write(f'{section} = {value}\n')


if __name__ == "__main__":
    # Usage Example
    config_loader = ConfigLoader('config.ini')

    # Get a config object for a specific section
    image_player_config = config_loader.get_config('ImagePlayer')
    if image_player_config:
        print(image_player_config.get('image_directory'))
        print(config_loader('ImagePlayer')('image_directory'))

    # Set a config value in a specific section
    config_loader.set_config('ImagePlayer', 'new_key', 'new_value')
    config_loader('ImagePlayer').set('new_key', 'new_value')

    # Save all configs to file
    config_loader.save('new_config.ini')

#!/usr/bin/python
# -*- coding: utf-8 -*-

import javalang
from os import makedirs, listdir, path
from os.path import isfile, join

ENTITIES_FOLDER = 'entities'
REPOSITORIES_FOLDER = 'repositories'
SERVICES_FOLDER = 'services'
BASE_PACKAGE = 'com.luanvv.spring.jpa'

EXCLUDE_FIELD = []


def is_id_annotation(field):
    return any(ann.name in ['Id', 'EmbeddedId'] for ann in
               field.annotations)


def is_transient(field):
    return any(ann.name in ['Transient'] for ann in field.annotations)


def is_one_many(field):
    return any(ann.name in ['OneToMany'] for ann in field.annotations)


def upper_first(name):
    return name[0].upper() + name[1:]


def lower_first(name):
    return name[0].lower() + name[1:]


def get_tree(f):
    data = read_file(f)
    return javalang.parse.parse(data)


def read_file(file):
    with open(file, 'r') as f:
        data = f.read()
    return data


def get_trees():
    mypath = ENTITIES_FOLDER
    trees = []
    for f in [f for f in listdir(mypath) if isfile(join(mypath, f))
              and not f.endswith('PK.java')
              and not f.endswith('_.java')]:
        trees.append(get_tree(mypath + '/' + f))
    return trees


def get_find_by_methods(tree, class_name = None, fields = None, method_type = 0): 
    # method_type: 0 for repository, 1 for service interface and 2 for service class implement
    # TODO use yeild
    repository_methods = []
    if class_name is None:
        class_name = get_class_name(tree)
    if fields is None:
        fields = get_fields(tree)
    end_method_point = ';' if method_type in [0, 1] else ' {'
    for field in fields:
        field_name = get_field_name(field)
        field_type = field.type.name
        if is_ignore_field(field):
            continue
        method_name = None
        if is_id_annotation(field):
            method_name = 'findOne'
            repository_methods.append('\tOptional<{0}> {1}({2} {3}){4}'.format(class_name,
                    method_name,
                    field.type.name, 
                    'id', 
                    end_method_point))
        else:
            method_name = 'findBy{0}'.format(upper_first(get_field_name(field)))
            repository_methods.append('\tList<{0}> {1}({2} {3}){4}'.format(class_name,
                                  method_name, 
                                  field_type,
                                  lower_first(field_name),
                                  end_method_point))
        if method_type == 2:
            repository_methods.append('\t\treturn dao.{0}({1});'.format(method_name, lower_first(field_name)))
            repository_methods.append('\t}')
        repository_methods.append('')
    return repository_methods

def get_fields(tree):
    return [f for f in tree.types[0].body if type(f).__name__
            == 'FieldDeclaration']


def get_class_name(tree):
    return tree.types[0].name


def is_ignore_field(field):
    if is_transient(field):
        return True
    if is_one_many(field):
        return True
    if len(field.type.dimensions):
        return True
    if get_field_name(field) in EXCLUDE_FIELD:
        return True
    return False


def get_wrapper_type(field_type):
    if field_type == 'int':
        return 'Integer'
    if field_type in ['long', 'double', 'float']:
        return upper_first(field_type)
    return field_type


def get_id(fields):
    for field in fields:
        if is_id_annotation(field):
            return {'name': get_field_name(field),
                    'type': get_wrapper_type(field.type.name)}
    raise ValueError('Cannot find primary key')

def get_field_name(field):
    return field.declarators[0].name
def get_repository(
    tree,
    class_name=None,
    id=None,
    fields=None,
    ):

    if class_name is None:
        class_name = get_class_name(tree)
    if fields is None:
        fields = get_fields(tree)
    if id is None:
        id = get_id(fields)
    line_packages = ['package {0}.{1};'.format(BASE_PACKAGE,
                     REPOSITORIES_FOLDER),
                    '']

    line_imports = []
    line_imports.append('import org.springframework.data.repository.JpaRepository;'
                        )
    line_imports.append('import org.springframework.stereotype.Repository;'
                        )
    line_imports.append('')
    lines = []
    lines.append('@Repository')
    lines.append('public interface {0}Dao  extends JpaRepository<{1}, {2}> {{'.format(class_name, class_name, id['type']))
    lines.append('')
    line_methods = get_find_by_methods(tree, class_name = class_name, fields = fields)

    lines = line_packages + line_imports + lines + line_methods

    lines.append('}')
    return '\n'.join(lines)

def get_service(
    tree,
    class_name=None,
    id=None,
    fields=None,
    ):

    if class_name is None:
        class_name = get_class_name(tree)
    if fields is None:
        fields = get_fields(tree)
    if id is None:
        id = get_id(fields)
    line_packages = ['package {0}.{1};'.format(BASE_PACKAGE,
                     SERVICES_FOLDER),
                    '']

    line_imports = []
    line_imports.append('import org.springframework.stereotype.Service;'
                        )
    line_imports.append('import org.springframework.transaction.annotation.Transactional;'
                        )
    line_imports.append('')

    lines = []
    
    lines.append('@Transactional(readOnly = true)')
    lines.append('@Service')
    lines.append('public interface {0}Service {{'.format(class_name))
    lines.append('')

    line_methods = get_find_by_methods(tree, class_name = class_name, fields = fields, method_type = 1)

    lines = line_packages + line_imports + lines + line_methods

    lines.append('}')
    return '\n'.join(lines)

def get_service_impl(
    tree,
    class_name=None,
    id=None,
    fields=None,
    ):

    if class_name is None:
        class_name = get_class_name(tree)
    if fields is None:
        fields = get_fields(tree)
    if id is None:
        id = get_id(fields)
    line_packages = ['package {0}.{1};'.format(BASE_PACKAGE,
                     SERVICES_FOLDER),
                    '']

    line_imports = []
    line_imports.append('import org.springframework.stereotype.Component;')
    line_imports.append('import org.springframework.beans.factory.annotation.Autowired;')
    line_imports.append('')

    lines = []
    
    lines.append('@Component')
    lines.append('public class {0}ServiceImpl implements {0}Service {{'.format(class_name))
    lines.append('')
    lines.append('\t@Autowired')
    lines.append('\tprivate {0}Dao dao;'.format(class_name))
    lines.append('')

    line_methods = get_find_by_methods(tree, class_name = class_name, fields = fields, method_type = 2)

    lines = line_packages + line_imports + lines + line_methods

    lines.append('}')
    return '\n'.join(lines)

def write_file(filename, data):
    makedirs(path.dirname(filename), exist_ok=True)
    with open(filename, 'wb') as f:
        # f.write(data)
        f.write(data.encode("UTF-8"))

def main():
    for tree in get_trees():
        print('Check class {0}'.format(get_class_name(tree)))
        class_name = get_class_name(tree)
        write_file('{0}/{1}Dao.java'.format(REPOSITORIES_FOLDER, class_name), get_repository(tree))
        write_file('{0}/{1}Service.java'.format(SERVICES_FOLDER, class_name), get_service(tree))
        write_file('{0}/{1}ServiceImpl.java'.format(SERVICES_FOLDER, class_name), get_service_impl(tree))

if __name__ == '__main__':
    main()

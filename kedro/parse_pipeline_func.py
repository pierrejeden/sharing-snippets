import ast
import inspect
import enum
import dataclasses
import ast

ID_PREFIX = 'id:'
REFERENCE_PREFIX = 'ref:'

NODE_ATTRIBUTE = '__NODE'
PIPELINE_ATTRIBUTE = '__PIPELINE'

class NodeKind(enum.Enum):
    FUNC = 'FUNC'


@dataclasses.dataclass
class Node:
    kind: NodeKind
    name: str = None
    func: callable = None
    namespace: str = ''
    inner_namespace: str = ''
    inputs: dict = dataclasses.field(default_factory=dict)
    outputs: list[str] = dataclasses.field(default_factory=list)
    children: list['Node'] = dataclasses.field(default_factory=list)
    is_pipeline: bool = False
    is_node: bool = False


def as_pipeline(f):
    setattr(f, PIPELINE_ATTRIBUTE, True)
    return f


def as_node(f):
    setattr(f, NODE_ATTRIBUTE, True)
    return f


def get_arg_names(func: callable) -> list[str]:
    """Get the names of the arguments of a function."""
    argspec = inspect.getfullargspec(func)
    # check if function has varaible number of arguments only
    if argspec.varargs is not None and argspec.args == []:
        return ['*args']
    return list(inspect.signature(func).parameters.keys())


def is_assign_call(node):
    if not isinstance(node, ast.Assign):
        return False
    if not isinstance(node.value, ast.Call):
        return False
    return True


def parse_assign_call(ast_node, namespace, module_vars):
    if isinstance(ast_node.targets[0], ast.Tuple):
        assigned_names = [el.id for el in ast_node.targets[0].elts]
    else:
        assigned_names = [ast_node.targets[0].id]

    called_func_name, called_func = get_name_func_from_call_node(node=ast_node.value, module_vars=module_vars)
    passed_kwargs = get_passed_args_as_kwargs(func=called_func, call=ast_node.value)
    node = Node(
        kind=NodeKind.FUNC,
        name=called_func_name,
        func=called_func,
        namespace=namespace,
        inner_namespace=f'{namespace}.{called_func_name}'.strip('.'),
        inputs=passed_kwargs,
        outputs=assigned_names,
        is_node=hasattr(called_func, NODE_ATTRIBUTE),
        is_pipeline=hasattr(called_func, PIPELINE_ATTRIBUTE),
    )
    return node


def get_name_func_from_call_node(node: ast.Call, module_vars):
    if isinstance(node.func, ast.Name):
        func_name = node.func.id
        func = module_vars[func_name]
    elif isinstance(node.func, ast.Attribute):
        obj_name = node.func.value.id
        func_name = node.func.attr
        func = module_vars[obj_name].__dict__[func_name]
    return func_name, func


def get_passed_args_as_kwargs(func: callable, call: ast.Call):
    passed_args = get_passed_args(call=call)
    passed_kwargs = get_passed_kwargs(call=call)
    arg_names = get_arg_names(func)
    all_kwargs = {arg_names[i]: a for i, a in enumerate(passed_args)}

    for k, v in passed_kwargs.items():
        all_kwargs[k] = v

    return all_kwargs


def get_passed_kwargs(call: ast.Call):
    passed = {}
    for kw in call.keywords:
        if isinstance(kw.value, (ast.Constant, ast.List)):
            passed[kw.arg] = kw.value.value
        elif isinstance(kw.value, (ast.Name, ast.Attribute)):
            arg_id = recursively_parse_ast_attribute(kw.value)
            passed[kw.arg] = f'id:{arg_id}'
        else:
            raise TypeError(f"type {type(kw.value)}")

    return passed


def get_passed_args(call: ast.Call):
    passed = []
    for arg in call.args:
        if isinstance(arg, (ast.Constant, ast.List)):
            passed.append(arg.value)
        elif isinstance(arg, (ast.Name, ast.Attribute)):
            arg_id = recursively_parse_ast_attribute(arg)
            passed.append(f'id:{arg_id}')
        else:
            raise TypeError(f"type {type(arg)}")
    return passed


def recursively_parse_ast_attribute(node, current_id=''):
    if isinstance(node, ast.Name):
        return f'{node.id}.{current_id}'.strip('.')
    if not isinstance(node, ast.Attribute):
        raise TypeError(f'Expected ast.Attribute or ast.Name, got {type(node)}')
    return recursively_parse_ast_attribute(node.value, f'{node.attr}.{current_id}').strip('.')


def deep_getattr(ob, dotkley):
    key_list = dotkley.split(".")
    for key in key_list:
        ob = getattr(ob, key)
    return ob


def parse_pipeline_function(
        func,  # : callable | list[callable],
        namespace: str = '',
):

    module_vars = inspect.getmodule(func).__dict__
    module_ast = ast.parse(source=inspect.getsource(func))
    func_ast = module_ast.body[0]

    pipeline_def = parse_ast_body(ast_body=func_ast.body, namespace=namespace, module_vars=module_vars)

    pipeline_def = deduplicate_children(pipeline_def)

    if namespace == '':
        top_inputs = get_arg_names(func)
        input_def = {k: f'id:{k}' for k in top_inputs}
        top_node = Node(
            kind=NodeKind.FUNC,
            name=func.__name__,
            func=func,
            inputs=input_def,
            outputs=get_return_names(func_ast=func_ast),
            children=pipeline_def,
            namespace=namespace,
            inner_namespace=namespace,
            is_pipeline=True,
        )
        return top_node

    return pipeline_def


def parse_ast_body(ast_body, namespace, module_vars):
    pipeline_def = []
    for ast_node in ast_body:

        node_def = None

        if is_assign_call(ast_node):
            node_def = parse_assign_call(ast_node=ast_node, namespace=namespace, module_vars=module_vars)
            if node_def.is_pipeline:
                # enter subpipeline
                func_ast = ast.parse(source=inspect.getsource(node_def.func)).body[0]
                return_names = get_return_names(func_ast=func_ast)
                node_def.children = parse_pipeline_function(
                    func=node_def.func,
                    namespace=f'{namespace}.{node_def.name}'.strip('.'),
                )

                # udpate the node_def ouutputs to a mapping outer_assign_name:return_name
                new_outputs = [f'{assign_name}:{return_name}' for assign_name, return_name in zip(node_def.outputs, return_names)]
                node_def.outputs = new_outputs

        else:
            print(f'NotImplementedWarning: Node type {type(ast_node)} not implemented')

        # deduplicate children for now...
        if node_def is None:
            continue
        if len(node_def.children) > 1:
            if is_same(node_def.children[0], node_def.children[1]):
                print('!!!!!!! ---------- deduplicating children')
                node_def.children = [node_def.children[0]]

        pipeline_def.append(node_def)

    return pipeline_def


def deduplicate_children(children):
    new_children = []
    for child in children:
        if not any([is_same(child, ch) for ch in new_children]):
            new_children.append(child)
        else:
            print('!!!!!!! ---------- deduplicating children')

    return new_children


def is_same(n1: Node, n2: Node) -> bool:
    same_names = n1.name == n2.name
    same_inputs = n1.inputs == n2.inputs
    same_outputs = n1.outputs == n2.outputs
    same_namespace = n1.namespace == n2.namespace
    same_inner_namespace = n1.inner_namespace == n2.inner_namespace
    return same_names and same_inputs and same_outputs and same_namespace and same_inner_namespace


def get_return_names(func_ast):
    assert isinstance(func_ast, ast.FunctionDef)
    assert isinstance(func_ast.body[-1], ast.Return)
    return_node = func_ast.body[-1]
    if isinstance(return_node.value, ast.Name):
        return [return_node.value.id]
    elif isinstance(return_node.value, ast.Tuple):
        return [elt.id for elt in return_node.value.elts]
    else:
        raise ValueError(f'Unsupported return node type: {type(return_node.value)}')
   

# simple example:
@as_node
def node_1(data_1, param_1):
    data_2 = data_1 + param_1
    return data_2


@as_node
def node_2(data_2, param_2):
    data_3 = data_2 + param_2
    return data_3

@as_node
def node_3(data_3, param_3):
    data_4 = data_3 + param_3
    return data_4

@as_node
def node_4(data_4, param_4):
    data_5 = data_4 + param_4
    return data_5

@as_pipeline
def sub_pipe_1(params, data_1):
    data_2 = node_3(data_3=data_1, param_3=params.param_3)
    data_3 = node_4(data_4=data_2, param_4=params.param_4)
    return data_3
   

@as_pipeline
def pipeline(params, data):
    data_1 = node_1(data_1=data, param_1=params.param_1)
    data_2 = node_2(data_2=data_1, param_2=params.param_2)
    data_3 = sub_pipe_1(params=params, data_1=data_2)
    return data_3

def print_node(node, indent=0):
    ind = 4 * indent * ' '
    nsname_str = f"{node.namespace}.{node.name}".strip('.')
    if node.is_pipeline:
       
        print(f"{ind}{nsname_str}: {node.inputs} -> {node.outputs}\n")
        for child in node.children:
            print_node(child, indent+1)      
    else:
        print(f"{ind}{nsname_str}: {node.inputs} -> {node.outputs}\n")


if __name__ == '__main__':
    pipeline_def = parse_pipeline_function(
        func=pipeline,
        namespace='',
    )
    print('--------------------------------')
    print_node(pipeline_def)
   
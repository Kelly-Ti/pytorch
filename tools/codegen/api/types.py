from tools.codegen.model import *
from dataclasses import dataclass
from typing import Optional, Union, Sequence, TypeVar, List, Set
from enum import Enum

_T = TypeVar('_T')

# An ArgName is just the str name of the argument in schema;
# but in some special circumstances, we may add a little extra
# context.  The Enum SpecialArgName covers all of these cases;
# grep for their construction sites to see when they can occr.

SpecialArgName = Enum('SpecialArgName', (
    'possibly_redundant_memory_format',
))
ArgName = Union[str, SpecialArgName]

# A CType is short for C++ semantic type.  A CType represents a C++ type, plus
# semantic information about what it represents.  For example, consider the
# argument "bool pin_memory"; its normal C++ type is "bool", but its C++
# semantic type also keeps track that this represents a "pin_memory"; you can't
# just use a random other boolean in a context where you need a "pin_memory"!
#
# CTypes encode C++ type structure as needed for translation.  Right now we
# track references and optional, but don't, for example, track ArrayRef.  If
# you need trnsnlations that know about these types, beef up this data
# structure.


# Prints an enum without the enum class name
class PrintEnum(Enum):
    def __str__(self):
        return self.name

# The set of all non-templated, valid, fully-qualified names of C++ types that are used in the codegen.
# Templated types get their own dataclass, mainly to make namespace parsing easier.
BaseCppType = PrintEnum('BaseCppType', (
    'int64_t',
    'double',
    'bool',
    'void',
    'std::string',
    'at::Generator',
    'at::ScalarType',
    'at::Tensor',
    'at::TensorList',
    'at::Dimname',
    'at::DimnameList',
    'at::Layout',
    'at::Device',
    'at::Scalar',
    'at::MemoryFormat',
    'at::QScheme',
    'at::Storage',
    'at::Stream',
    'at::IntArrayRef',
    'at::TensorOptions',
))

@dataclass(unsafe_hash=True)
class BaseCType:
    type: BaseCppType
    name: ArgName

    def __init__(self, ty: str, name: ArgName):
        # BaseCType checks that the type that you pass in is a valid C++ type.
        # For convenience, we assume that the "standard" pytorch namespaces are in-scope.
        in_scope_namespaces = ['', 'at::', 'c10::']
        # Simple namespace resolution rules: try every in-scope namespace before declaring a type to be invalid.
        baseCppType = None
        for ns in in_scope_namespaces:
            namespaced_ty = f'{ns}{ty}'
            if namespaced_ty in BaseCppType.__members__:
                baseCppType = BaseCppType[namespaced_ty]
        assert baseCppType is not None, f"Received invalid C++ type: {ty}"
        self.type = baseCppType
        self.name = name

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        return str(self.type)

    # For BC reasons, we don't want to introduce at:: namespaces to RegistrationDeclarations.yaml
    # TODO: Kill this when we eventually remove it!
    def cpp_type_remove_namespaces(self) -> str:
        return str(self.type).replace('at::', '')

@dataclass(frozen=True)
class ConstRefCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        if strip_ref:
            return self.elem.cpp_type(strip_ref=strip_ref)
        return f'const {self.elem.cpp_type()} &'

    def cpp_type_remove_namespaces(self) -> str:
        return f'const {self.elem.cpp_type_remove_namespaces()} &'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class MutRefCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        if strip_ref:
            return self.elem.cpp_type(strip_ref=strip_ref)
        return f'{self.elem.cpp_type()} &'

    def cpp_type_remove_namespaces(self) -> str:
        return f'{self.elem.cpp_type_remove_namespaces()} &'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class OptionalCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'c10::optional<{self.elem.cpp_type()}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'c10::optional<{self.elem.cpp_type_remove_namespaces()}>'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class ListCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'c10::List<{self.elem.cpp_type()}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'c10::List<{self.elem.cpp_type_remove_namespaces()}>'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class ArrayRefCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'at::ArrayRef<{self.elem.cpp_type()}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'at::ArrayRef<{self.elem.cpp_type_remove_namespaces()}>'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class VectorCType:
    elem: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'std::vector<{self.elem.cpp_type()}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'std::vector<{self.elem.cpp_type_remove_namespaces()}>'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class ArrayCType:
    elem: 'CType'
    size: int

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'std::array<{self.elem.cpp_type()},{self.size}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'std::array<{self.elem.cpp_type_remove_namespaces()}, {self.size}>'

    @property
    def name(self) -> ArgName:
        return self.elem.name

@dataclass(frozen=True)
class TupleCType:
    elems: 'CType'

    def cpp_type(self, *, strip_ref: bool = False) -> str:
        # Do not pass `strip_ref` recursively.
        return f'std::tuple<{",".join([e.cpp_type() for e in self.elems])}>'

    def cpp_type_remove_namespaces(self) -> str:
        return f'std::tuple<{",".join([e.cpp_type_remove_namespaces() for e in self.elems])}>'

    @property
    def name(self) -> ArgName:
        # N.B. this isn't currently used anywhere: std::tuple is only used as a return type, which doesn't use names.
        assert_never("std::tuple isn't currently used as an argument anywhere, and doesn't require a name.")
        return self.name

CType = Union[BaseCType, OptionalCType, ConstRefCType, MutRefCType, ListCType, ArrayRefCType, VectorCType, TupleCType]

# A binding represents any C++ binding site for a formal parameter.
# We don't distinguish between binding sites for different APIs;
# instead, all of the important distinctions are encoded in CType,
# which you can use to figure out if a given Binding is appropriate
# for use in another context.  (See tools.codegen.api.translate)

@dataclass(frozen=True)
class Binding:
    name: str
    ctype: CType
    argument: Union[Argument, TensorOptionsArguments, SelfArgument]
    # TODO: maybe don't represent default here
    default: Optional[str] = None

    @property
    def type(self) -> str:
        return self.ctype.cpp_type()

    def no_default(self) -> 'Binding':
        return Binding(
            name=self.name,
            ctype=self.ctype,
            default=None,
            argument=self.argument,
        )

    def decl(self) -> str:
        mb_default = ""
        if self.default is not None:
            mb_default = f"={self.default}"
        return f"{self.type} {self.name}{mb_default}"

    # For BC reasons, we don't want to introduce at:: namespaces to RegistrationDeclarations.yaml
    # TODO: Kill this when we eventually remove it!
    def decl_remove_namespaces(self) -> str:
        type_s = self.ctype.cpp_type_remove_namespaces()
        mb_default = ""
        if self.default is not None:
            mb_default = f"={self.default}"
        return f"{type_s} {self.name}{mb_default}"

    def defn(self) -> str:
        return f"{self.type} {self.name}"

# An Expr is a C++ expression.  It has a C++ string representing its syntax,
# as well as a CType saying what it provides.

@dataclass(frozen=True)
class Expr:
    expr: str
    type: CType

# A CppSignature represents a single overload in the C++ API.  For
# any given function schema, there may be multiple CppSignatures
# corresponding to it, based on how we desugar to C++.  See also
# CppSignatureGroup.
@dataclass(frozen=True)
class CppSignature:
    # The schema this signature is derived from
    func: FunctionSchema

    # Is this a C++ signature for a method, i.e. Tensor::my_op(...)?
    method: bool

    # Is this a faithful C++ signature (i.e. following the JIT schema) or a convenience API
    # (i.e. with a potential TensorOptions argument and out arguments in the front)
    faithful: bool

    # The set of C++ arguments which should not have defaults applied to them
    cpp_no_default_args: Set[str]

    # Is this a fallback C++ binding?  Fallback bindings are enabled by
    # manual_cpp_binding: True and are alternate, non-public API that
    # lets manual C++ binding implementors access the binding that would
    # have been automatically generated
    fallback_binding: bool = False

    # Return the unpacked argument structure of this signature,
    # discarding information about which arguments are semantically
    # related to each other.
    def arguments(self) -> Sequence[Binding]:
        return cpp.arguments(
            self.func.arguments, faithful=self.faithful,
            method=self.method, cpp_no_default_args=self.cpp_no_default_args)

    def name(self) -> str:
        n = cpp.name(self.func, faithful_name_for_out_overloads=self.faithful)
        if self.fallback_binding:
            n = f"__dispatch_{n}"
        return n

    # Render the C++ declaration for this signature
    def decl(self, *, prefix: str = "", is_redispatching_fn: bool = False) -> str:
        returns_type = cpp.returns_type(self.func.returns).cpp_type()
        cpp_args = [a.decl() for a in self.arguments()]
        if is_redispatching_fn:
            cpp_args = ['c10::DispatchKeySet dispatchKeySet'] + cpp_args
        cpp_args_str = ', '.join(cpp_args)
        name = prefix + self.name()
        return f"{returns_type} {name}({cpp_args_str})"

    # Render the C++ definition for this signature, not including
    # the body (with curly braces)
    def defn(self, *, prefix: str = "", is_redispatching_fn: bool = False) -> str:
        returns_type = cpp.returns_type(self.func.returns).cpp_type()
        cpp_args = [a.defn() for a in self.arguments()]
        if is_redispatching_fn:
            cpp_args = ['c10::DispatchKeySet dispatchKeySet'] + cpp_args
        cpp_args_str = ', '.join(cpp_args)
        name = prefix + self.name()
        return f"{returns_type} {name}({cpp_args_str})"


# Represents group of all CppSignatures associated with a
# FunctionSchema.  Right now, that's the regular, user-visible
# signature, as well as a "faithful" signature which doesn't
# have grouping.
@dataclass(frozen=True)
class CppSignatureGroup:
    func: FunctionSchema
    signature: CppSignature
    faithful_signature: Optional[CppSignature]

    def most_faithful_signature(self) -> CppSignature:
        if self.faithful_signature:
            return self.faithful_signature
        else:
            return self.signature

    @staticmethod
    def from_native_function(f: NativeFunction, *, method: bool, fallback_binding: bool = False) -> 'CppSignatureGroup':
        func = f.func
        faithful_signature: Optional[CppSignature]
        if func.arguments.tensor_options is not None or len(func.arguments.out) > 0:
            faithful_signature = CppSignature(
                func=func,
                faithful=True,
                method=method,
                fallback_binding=fallback_binding,
                cpp_no_default_args=f.cpp_no_default_args
            )
        else:
            faithful_signature = None
        signature = CppSignature(
            func=func,
            faithful=False,
            method=method,
            fallback_binding=fallback_binding,
            cpp_no_default_args=f.cpp_no_default_args
        )
        return CppSignatureGroup(
            func=func,
            signature=signature,
            faithful_signature=faithful_signature,
        )

@dataclass(frozen=True)
class DispatcherSignature:
    # The schema this signature is derived from
    func: FunctionSchema

    def arguments(self) -> List[Binding]:
        return dispatcher.arguments(self.func)

    def name(self) -> str:
        return dispatcher.name(self.func)

    def defn(self, name: Optional[str] = None) -> str:
        args_str = ', '.join(a.defn() for a in self.arguments())
        if name is None:
            name = self.name()
        return f"{self.returns_type().cpp_type()} {name}({args_str})"

    def exprs(self) -> List[Expr]:
        return [Expr(a.name, a.ctype) for a in self.arguments()]

    def returns_type(self) -> CType:
        return dispatcher.returns_type(self.func.returns)

    # Return the C++ function type, e.g., something like int(bool)
    def type(self) -> str:
        dispatcher_args_types_str = ', '.join(a.type for a in self.arguments())
        return f'{self.returns_type().cpp_type()} ({dispatcher_args_types_str})'

    @staticmethod
    def from_schema(func: FunctionSchema) -> 'DispatcherSignature':
        return DispatcherSignature(func)

@dataclass(frozen=True)
class NativeSignature:
    # The schema this signature is derived from
    func: FunctionSchema

    prefix: str = ""

    def name(self) -> str:
        return self.prefix + native.name(self.func)

    def defn(self, name: Optional[str] = None) -> str:
        args_str = ', '.join(a.defn() for a in self.arguments())
        if name is None:
            name = self.name()
        return f"{native.returns_type(self.func.returns).cpp_type()} {name}({args_str})"

    def ptr_type(self) -> str:
        # don't include defaults in type signature!
        args_str = ', '.join(a.defn() for a in self.arguments())
        return f'{native.returns_type(self.func.returns).cpp_type()} (*)({args_str})'

    def arguments(self) -> List[Binding]:
        return native.arguments(self.func)

    def returns_type(self) -> CType:
        return native.returns_type(self.func.returns)

    def dispatcher_exprs(self) -> List[Expr]:
        return translate.translate(self.arguments(), dispatcher.arguments(self.func), method=False)

# Functions only, no types
from tools.codegen.api import cpp, dispatcher, native, translate

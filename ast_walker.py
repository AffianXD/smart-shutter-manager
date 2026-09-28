import ast
import builtins
import sys
import glob
import os

BUILTIN_NAMES = set(dir(builtins))


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.names = set()

    def define(self, name):
        self.names.add(name)

    def is_defined(self, name):
        s = self
        while s is not None:
            if name in s.names:
                return True
            s = s.parent
        return name in BUILTIN_NAMES


class UndefinedNameChecker(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.errors = []
        self.global_scope = Scope()
        for n in ("__name__", "__file__", "__doc__", "__package__", "__builtins__", "__spec__", "__loader__"):
            self.global_scope.define(n)

    def visit_Module(self, node):
        self._collect_toplevel_defs(node.body, self.global_scope)
        self.generic_visit_body(node.body, self.global_scope)

    def _collect_toplevel_defs(self, body, scope):
        for stmt in body:
            self._predefine(stmt, scope)

    def _predefine(self, stmt, scope):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.define(stmt.name)
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                self._define_target(t, scope)
        elif isinstance(stmt, ast.AnnAssign):
            self._define_target(stmt.target, scope)
        elif isinstance(stmt, ast.AugAssign):
            self._define_target(stmt.target, scope)
        elif isinstance(stmt, (ast.Import,)):
            for alias in stmt.names:
                name = alias.asname or alias.name.split(".")[0]
                scope.define(name)
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                name = alias.asname or alias.name
                scope.define(name)
        elif isinstance(stmt, ast.If):
            for s in stmt.body:
                self._predefine(s, scope)
            for s in stmt.orelse:
                self._predefine(s, scope)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            self._define_target(stmt.target, scope)
            for s in stmt.body:
                self._predefine(s, scope)
            for s in stmt.orelse:
                self._predefine(s, scope)
        elif isinstance(stmt, ast.While):
            for s in stmt.body:
                self._predefine(s, scope)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars:
                    self._define_target(item.optional_vars, scope)
            for s in stmt.body:
                self._predefine(s, scope)
        elif isinstance(stmt, ast.Try):
            for s in stmt.body:
                self._predefine(s, scope)
            for h in stmt.handlers:
                if h.name:
                    scope.define(h.name)
                for s in h.body:
                    self._predefine(s, scope)
            for s in stmt.orelse:
                self._predefine(s, scope)
            for s in stmt.finalbody:
                self._predefine(s, scope)

    def _define_target(self, target, scope):
        if isinstance(target, ast.Name):
            scope.define(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._define_target(elt, scope)
        elif isinstance(target, ast.Starred):
            self._define_target(target.value, scope)

    def generic_visit_body(self, body, scope):
        for stmt in body:
            self.visit_stmt(stmt, scope)

    def visit_stmt(self, stmt, scope):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.check_function(stmt, scope)
        elif isinstance(stmt, ast.ClassDef):
            for dec in stmt.decorator_list:
                self.check_expr(dec, scope)
            for base in stmt.bases:
                self.check_expr(base, scope)
            class_scope = Scope(scope)
            self._collect_toplevel_defs(stmt.body, class_scope)
            self.generic_visit_body(stmt.body, class_scope)
        elif isinstance(stmt, ast.Assign):
            self.check_expr(stmt.value, scope)
        elif isinstance(stmt, ast.AnnAssign):
            if stmt.value:
                self.check_expr(stmt.value, scope)
        elif isinstance(stmt, ast.AugAssign):
            self.check_expr(stmt.value, scope)
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                self.check_expr(stmt.value, scope)
        elif isinstance(stmt, ast.Expr):
            self.check_expr(stmt.value, scope)
        elif isinstance(stmt, ast.If):
            self.check_expr(stmt.test, scope)
            self.generic_visit_body(stmt.body, scope)
            self.generic_visit_body(stmt.orelse, scope)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            self.check_expr(stmt.iter, scope)
            self.generic_visit_body(stmt.body, scope)
            self.generic_visit_body(stmt.orelse, scope)
        elif isinstance(stmt, ast.While):
            self.check_expr(stmt.test, scope)
            self.generic_visit_body(stmt.body, scope)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                self.check_expr(item.context_expr, scope)
            self.generic_visit_body(stmt.body, scope)
        elif isinstance(stmt, ast.Try):
            self.generic_visit_body(stmt.body, scope)
            for h in stmt.handlers:
                if h.type:
                    self.check_expr(h.type, scope)
                self.generic_visit_body(h.body, scope)
            self.generic_visit_body(stmt.orelse, scope)
            self.generic_visit_body(stmt.finalbody, scope)
        elif isinstance(stmt, ast.Raise):
            if stmt.exc:
                self.check_expr(stmt.exc, scope)
            if stmt.cause:
                self.check_expr(stmt.cause, scope)
        elif isinstance(stmt, ast.Assert):
            self.check_expr(stmt.test, scope)
            if stmt.msg:
                self.check_expr(stmt.msg, scope)

    def check_function(self, fn, outer_scope):
        for dec in fn.decorator_list:
            self.check_expr(dec, outer_scope)
        fn_scope = Scope(outer_scope)
        args = fn.args
        all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
        for a in all_args:
            fn_scope.define(a.arg)
        if args.vararg:
            fn_scope.define(args.vararg.arg)
        if args.kwarg:
            fn_scope.define(args.kwarg.arg)
        for d in args.defaults:
            self.check_expr(d, outer_scope)
        for d in args.kw_defaults:
            if d:
                self.check_expr(d, outer_scope)
        self._collect_toplevel_defs(fn.body, fn_scope)
        self.generic_visit_body(fn.body, fn_scope)

    def check_expr(self, node, scope):
        if node is None:
            return
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load) and not scope.is_defined(node.id):
                self.errors.append(
                    f"{self.filename}:{node.lineno}: possibly undefined name '{node.id}'"
                )
        elif isinstance(node, ast.Lambda):
            lam_scope = Scope(scope)
            args = node.args
            all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            for a in all_args:
                lam_scope.define(a.arg)
            if args.vararg:
                lam_scope.define(args.vararg.arg)
            if args.kwarg:
                lam_scope.define(args.kwarg.arg)
            self.check_expr(node.body, lam_scope)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            comp_scope = Scope(scope)
            for gen in node.generators:
                self.check_expr(gen.iter, comp_scope)
                self._define_target(gen.target, comp_scope)
                for cond in gen.ifs:
                    self.check_expr(cond, comp_scope)
            if isinstance(node, ast.DictComp):
                self.check_expr(node.key, comp_scope)
                self.check_expr(node.value, comp_scope)
            else:
                self.check_expr(node.elt, comp_scope)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self.check_expr(child, scope)
                elif isinstance(child, (ast.keyword,)):
                    self.check_expr(child.value, scope)


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    checker = UndefinedNameChecker(os.path.basename(path))
    checker.visit_Module(tree)
    return checker.errors


def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    files = sorted(glob.glob(os.path.join(target_dir, "*.py")))
    total_errors = []
    for f in files:
        errs = check_file(f)
        total_errors.extend(errs)
    if total_errors:
        print(f"{len(total_errors)} possible problems found:")
        for e in total_errors:
            print("  " + e)
        sys.exit(1)
    else:
        print(f"AST walker OK: {len(files)} files checked, no undefined names found")
        sys.exit(0)


if __name__ == "__main__":
    main()

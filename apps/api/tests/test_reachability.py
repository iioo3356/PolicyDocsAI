from app.analysis.reachability import select_reachable_react_files


def paths(files):
    return [path for path, _ in files]


def test_only_route_reachable_react_files_are_selected():
    documents = [
        ("project/src/app/orders/page.tsx", b"import OrderForm from '@/components/OrderForm'"),
        ("project/src/components/OrderForm.tsx", b"import { canCancel } from '../domain/orderPolicy'"),
        ("project/src/domain/orderPolicy.ts", b"export const canCancel = order => order.status !== 'SHIPPED'"),
        ("project/src/features/unused/Admin.tsx", b"if (user.status === 'BLOCKED') return null"),
        ("project/src/lib/api.ts", b"if (!response.ok) throw Error()"),
    ]

    selected, stats = select_reachable_react_files(documents)

    assert paths(selected) == [
        "project/src/app/orders/page.tsx",
        "project/src/components/OrderForm.tsx",
        "project/src/domain/orderPolicy.ts",
    ]
    assert stats == {"mode": "route-reachable", "entries": 1, "selected": 3, "ignored": 2}


def test_config_file_is_excluded_even_when_route_imports_it():
    documents = [
        ("src/pages/orders.tsx", b"import api from '../api'\nif (order.status) return null"),
        ("src/api.ts", b"if (!response.ok) throw Error()"),
    ]

    selected, _ = select_reachable_react_files(documents)

    assert paths(selected) == ["src/pages/orders.tsx"]


def test_non_react_archive_keeps_existing_all_code_behavior():
    documents = [("server/Policy.kt", b"if (status == CLOSED) return false")]

    selected, stats = select_reachable_react_files(documents)

    assert selected == documents
    assert stats["mode"] == "all-code-fallback"


def test_ast_follows_reexports_dynamic_imports_and_require_calls():
    documents = [
        ("src/app/page.tsx", b"export { PolicyView } from '../features'"),
        ("src/features/index.ts", b"export * from './PolicyView'"),
        ("src/features/PolicyView.tsx", b"const rules = import('./rules')\nconst legacy = require('./legacy')"),
        ("src/features/rules.ts", b"export const minimumAge = 19"),
        ("src/features/legacy.js", b"exports.enabled = true"),
        ("src/features/unused.ts", b"export const unused = true"),
    ]

    selected, _ = select_reachable_react_files(documents)

    assert paths(selected) == [
        "src/app/page.tsx",
        "src/features/PolicyView.tsx",
        "src/features/index.ts",
        "src/features/legacy.js",
        "src/features/rules.ts",
    ]


def test_ast_does_not_treat_import_like_text_as_a_dependency():
    documents = [
        ("src/pages/home.tsx", b"export const example = './unused'\nconst docs = \"import('./unused')\""),
        ("src/components/unused.tsx", b"export const secret = true"),
    ]

    selected, _ = select_reachable_react_files(documents)

    assert paths(selected) == ["src/pages/home.tsx"]

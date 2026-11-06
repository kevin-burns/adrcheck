from adrcheck.adapters.unified_diff import parse_patch

PATCH = """diff --git a/enrich/store.py b/enrich/store.py
index 1111111..2222222 100644
--- a/enrich/store.py
+++ b/enrich/store.py
@@ -10,4 +10,4 @@ def row_key(row):
 def save(row):
-    key = row["url"]
+    key = row_key(row)
     db[key] = row
     return key
diff --git a/enrich/new.py b/enrich/new.py
new file mode 100644
--- /dev/null
+++ b/enrich/new.py
@@ -0,0 +1,2 @@
+import requests
+SESSION = requests.Session()
"""


def test_added_and_removed_lines_carry_path_number_and_text():
    files = parse_patch(PATCH)
    store = files[0]
    assert store.path == "enrich/store.py"
    assert [(l.number, l.text) for l in store.removed] == [(11, '    key = row["url"]')]
    assert [(l.number, l.text) for l in store.added] == [(11, "    key = row_key(row)")]


def test_new_file_has_only_added_lines_and_a_dev_null_old_path():
    files = parse_patch(PATCH)
    new = files[1]
    assert new.path == "enrich/new.py"
    assert new.old_path is None
    assert [l.text for l in new.added] == ["import requests", "SESSION = requests.Session()"]
    assert new.removed == ()

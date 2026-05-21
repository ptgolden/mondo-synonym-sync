TMPDIR := tmp

update-synonyms-sync:
	mkdir -p $(TMPDIR)
	sed -i 's|EXACT \[DOID:1, NCIT:C1\]|EXACT [DOID:1, NCIT:C1, MGI:1]|' mondo-edit.obo

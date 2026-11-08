# ADR template corpus

One decision, "fold rows, never drop them", written by us in every common ADR shape. The words are ours; only
the section names follow each template. Templates are named for the shape they follow: Nygard (2011),
MADR 4 (adr.github.io/madr), Y-statements (Zimmermann), Tyree and Akerman (2005), arc42 section 9, the
Alexandrian pattern form, Planguage (Gilb), a business-case form, ITD and EdgeX, plus two house styles seen
in the wild (bold labels instead of headings; the decision in a table). Section names were taken from the
architecture-decision-record collection by Joel Parker Henderson and from the MADR site; no template body
text is copied.

Every fixture must parse to: status accepted; a binding role containing "folded, not dropped"; where the
shape has a rejected role, a sentence from it that `verify()` refuses as outside the decision; and an
explicit "no <role> section" rather than a guess where the shape has no such role.

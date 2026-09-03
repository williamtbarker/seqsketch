# Security policy

SeqSketch accepts local FASTA, JSONL, and JSON index files. Treat untrusted input as data and avoid
running the command with elevated privileges. The index format intentionally uses JSON rather than
executable pickle serialization.

Report suspected vulnerabilities privately through GitHub's security-advisory interface. Please
do not include confidential datasets in a report.


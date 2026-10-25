-- FC1/FC15/FC18: concentration tracks are requirement blocks (kind = 'concentration')
-- owned by one named track.
ALTER TABLE degree_requirement_blocks ADD COLUMN concentration TEXT;

CREATE EXTENSION postgis;
CREATE EXTENSION unaccent;
ALTER FUNCTION unaccent(text) IMMUTABLE;
CREATE DATABASE dota;

CREATE TABLE domains (
id SERIAL PRIMARY KEY,
domain varchar(255) NOT NULL,
disabled BOOLEAN DEFAULT FALSE,
added timestamp DEFAULT current_timestamp,
https BOOLEAN DEFAULT FALSE
);

CREATE TABLE MSE_latest_vs_recent (
id SERIAL PRIMARY KEY,
domain_id int references domains(id),
added timestamp DEFAULT current_timestamp,
score int not null,
latest_image_id int references images(id),
recent_image_id int references images(id)
);

CREATE TABLE MSE_recent_vs_base (
id SERIAL PRIMARY KEY,
domain_id int references domains(id),
added timestamp DEFAULT current_timestamp,
score int not null, 
base_image_id int references images(id),
recent_image_id int references images(id)
);

CREATE TABLE images(
id SERIAL PRIMARY KEY,
domain_id int references domains(id),
image_hash varchar(255) NOT NULL, --this is a sha256 hash
path_to_file text NOT NULL,
ocr_data text,
added timestamp DEFAULT current_timestamp,
tags text[]
);




drop table IF exists urls;
create table urls (
    id integer primary key autoincrement,
    url text not null,
    type text not null
);
commit;
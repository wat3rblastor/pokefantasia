CREATE DATABASE IF NOT EXISTS pokefantasia;


USE pokefantasia;


DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS users;


CREATE TABLE users
(
    userid       int not null AUTO_INCREMENT,
    username     varchar(64) not null,
    pwdhash      varchar(256) not null,
    PRIMARY KEY  (userid),
    UNIQUE       (username)
);

ALTER TABLE users AUTO_INCREMENT = 80001;  -- starting value

CREATE TABLE jobs
(
    jobid             int not null AUTO_INCREMENT,
    userid            int not null,
    status            varchar(256) not null,  -- uploaded, completed, error, processing...
    originaldatafile  varchar(256) not null,  -- original PNG filename from user
    datafilekey       varchar(256) not null,  -- PNG filename in S3 (bucketkey)
    resultsfilekey    varchar(256) not null,  -- results filename in S3 bucket
    bucket			  varchar(256) not null,  -- which S3 bucket it was placed in
    PRIMARY KEY (jobid),
    FOREIGN KEY (userid) REFERENCES users(userid),
    UNIQUE      (datafilekey)
);


ALTER TABLE jobs AUTO_INCREMENT = 1001;  -- starting value


--
-- Insert some users to start with:
-- 
-- PWD hashing: https://phppasswordhash.com/
--
INSERT INTO users(username, pwdhash)  -- pwd = abc123!!
            values('b_cheng', '$2y$10$/8B5evVyaHF.hxVx0i6dUe2JpW89EZno/VISnsiD1xSh6ZQsNMtXK');


INSERT INTO users(username, pwdhash)  -- pwd = abc456!!
            values('h_wang', '$2y$10$F.FBSF4zlas/RpHAxqsuF.YbryKNr53AcKBR3CbP2KsgZyMxOI2z2');


INSERT INTO users(username, pwdhash)  -- pwd = abc789!!
            values('s_zhu', '$2y$10$GmIzRsGKP7bd9MqH.mErmuKvZQ013kPfkKbeUAHxar5bn1vu9.sdK');


--
-- creating user accounts for database access:
--
-- ref: https://dev.mysql.com/doc/refman/8.0/en/create-user.html
--


DROP USER IF EXISTS 'pokefantasia-read-only';
DROP USER IF EXISTS 'pokefantasia-read-write';


CREATE USER 'pokefantasia-read-only' IDENTIFIED BY 'abc123!!';
CREATE USER 'pokefantasia-read-write' IDENTIFIED BY 'def456!!';


GRANT SELECT, SHOW VIEW ON pokefantasia.* 
      TO 'pokefantasia-read-only';
GRANT SELECT, SHOW VIEW, INSERT, UPDATE, DELETE, DROP, CREATE, ALTER ON pokefantasia.* 
      TO 'pokefantasia-read-write';
      
FLUSH PRIVILEGES;


--
-- done
--
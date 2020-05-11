--
-- PostgreSQL database dump
--

-- Dumped from database version 12.2
-- Dumped by pg_dump version 12.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: dvorak; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dvorak (
    ch character(1),
    hand character(1),
    digit integer,
    shifted boolean,
    "row" integer
);


--
-- Name: keystrokes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.keystrokes (
    text_id integer NOT NULL,
    user_id integer NOT NULL,
    race_date timestamp without time zone,
    race_id integer NOT NULL,
    ch_prev character(1),
    ch character(1),
    ms integer,
    forward_prev boolean,
    forward boolean,
    ch_index integer,
    seq_index integer NOT NULL
);


--
-- Name: qwerty; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.qwerty (
    ch character(1),
    hand character(1),
    digit integer,
    shifted boolean,
    "row" integer
);


--
-- Name: texts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.texts (
    text_id integer NOT NULL,
    raw_text text
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(32),
    type character varying
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: wpm; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wpm (
    user_id integer NOT NULL,
    race_date timestamp without time zone NOT NULL,
    race_id integer NOT NULL,
    wpm integer,
    accuracy real
);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: keystrokes keystrokes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keystrokes
    ADD CONSTRAINT keystrokes_pkey PRIMARY KEY (user_id, text_id, race_id, seq_index);


--
-- Name: texts texts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.texts
    ADD CONSTRAINT texts_pkey PRIMARY KEY (text_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: wpm wpm_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wpm
    ADD CONSTRAINT wpm_pkey PRIMARY KEY (user_id, race_date, race_id);


--
-- Name: keystrokes keystrokes_text_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keystrokes
    ADD CONSTRAINT keystrokes_text_id_fkey FOREIGN KEY (text_id) REFERENCES public.texts(text_id);


--
-- Name: keystrokes keystrokes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.keystrokes
    ADD CONSTRAINT keystrokes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: wpm wpm_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wpm
    ADD CONSTRAINT wpm_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: TABLE dvorak; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.dvorak TO typescraper;


--
-- Name: TABLE keystrokes; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.keystrokes TO typescraper;


--
-- Name: TABLE qwerty; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.qwerty TO typescraper;


--
-- Name: TABLE texts; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.texts TO typescraper;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO typescraper;


--
-- Name: SEQUENCE users_user_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,USAGE ON SEQUENCE public.users_user_id_seq TO typescraper;


--
-- Name: TABLE wpm; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.wpm TO typescraper;


--
-- PostgreSQL database dump complete
--


--
-- PostgreSQL database dump
--

\restrict K4EdAmZCyDUkFsBJqS82nhPTfxaMy0yIoJLeaXVa5mdYbd7nXwbo06ecva3Vunt

-- Dumped from database version 16.9
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: hsai_business_good_video_v1; Type: TABLE; Schema: public; Owner: hsai
--

CREATE TABLE public.hsai_business_good_video_v1 (
    id bigint NOT NULL,
    businessname character varying(255) NOT NULL,
    authorname text,
    authorid text,
    authorurl text,
    videourl text,
    music character varying(255),
    musicurl text,
    text text,
    hashtags text,
    video_type text,
    publishedtime timestamp with time zone,
    isad boolean DEFAULT false NOT NULL,
    diggcount bigint DEFAULT 0 NOT NULL,
    sharecount bigint DEFAULT 0 NOT NULL,
    playcount bigint DEFAULT 0 NOT NULL,
    collectcount bigint DEFAULT 0 NOT NULL,
    commentcount bigint DEFAULT 0 NOT NULL,
    createdat timestamp with time zone DEFAULT now() NOT NULL,
    updatedat timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.hsai_business_good_video_v1 OWNER TO hsai;

--
-- Name: hsai_business_good_video_v1_id_seq; Type: SEQUENCE; Schema: public; Owner: hsai
--

CREATE SEQUENCE public.hsai_business_good_video_v1_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hsai_business_good_video_v1_id_seq OWNER TO hsai;

--
-- Name: hsai_business_good_video_v1_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: hsai
--

ALTER SEQUENCE public.hsai_business_good_video_v1_id_seq OWNED BY public.hsai_business_good_video_v1.id;


--
-- Name: hsai_business_good_video_v1 id; Type: DEFAULT; Schema: public; Owner: hsai
--

ALTER TABLE ONLY public.hsai_business_good_video_v1 ALTER COLUMN id SET DEFAULT nextval('public.hsai_business_good_video_v1_id_seq'::regclass);


--
-- Name: hsai_business_good_video_v1 hsai_business_good_video_v1_pkey; Type: CONSTRAINT; Schema: public; Owner: hsai
--

ALTER TABLE ONLY public.hsai_business_good_video_v1
    ADD CONSTRAINT hsai_business_good_video_v1_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict K4EdAmZCyDUkFsBJqS82nhPTfxaMy0yIoJLeaXVa5mdYbd7nXwbo06ecva3Vunt


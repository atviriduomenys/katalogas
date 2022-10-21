-- Adminer 4.8.1 PostgreSQL 14.5 (Debian 14.5-1.pgdg110+1) dump

DROP TABLE IF EXISTS "adp_cms_page";
DROP SEQUENCE IF EXISTS adp_cms_page_id_seq;
CREATE SEQUENCE adp_cms_page_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."adp_cms_page" (
    "id" bigint DEFAULT nextval('adp_cms_page_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "body" text,
    "description" text,
    "page_order" bigint,
    "published" boolean NOT NULL,
    "slug" text,
    "title" text,
    "type" bigint,
    "parent_id" bigint,
    "language" character varying(255),
    "list_children" boolean NOT NULL,
    CONSTRAINT "idx_696610_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696610_fkh6y4ejn6r1yjtr6v8sa80u57p" ON "public"."adp_cms_page" USING btree ("parent_id");


DROP TABLE IF EXISTS "api_description";
DROP SEQUENCE IF EXISTS api_description_id_seq;
CREATE SEQUENCE api_description_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."api_description" (
    "id" bigint DEFAULT nextval('api_description_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "api_version" character varying(255),
    "contact_email" character varying(255),
    "contact_name" character varying(255),
    "contact_url" character varying(255),
    "desription_html" text,
    "identifier" character varying(255),
    "licence" character varying(255),
    "licence_url" character varying(255),
    "title" character varying(255),
    CONSTRAINT "idx_696617_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "api_key";
DROP SEQUENCE IF EXISTS api_key_id_seq;
CREATE SEQUENCE api_key_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."api_key" (
    "id" bigint DEFAULT nextval('api_key_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "api_key" character varying(255),
    "enabled" boolean,
    "expires" timestamptz,
    "organization_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696624_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696624_ukr6ixjob39jj0hsrmet0wqg14c" UNIQUE ("api_key")
) WITH (oids = false);

CREATE INDEX "idx_696624_fk2cifbfne14e6w1in2bjbs6sf6" ON "public"."api_key" USING btree ("organization_id");


DROP TABLE IF EXISTS "application_setting";
DROP SEQUENCE IF EXISTS application_setting_id_seq;
CREATE SEQUENCE application_setting_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."application_setting" (
    "id" bigint DEFAULT nextval('application_setting_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "name" character varying(255),
    "value" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696629_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "application_usecase";
DROP SEQUENCE IF EXISTS application_usecase_id_seq;
CREATE SEQUENCE application_usecase_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."application_usecase" (
    "id" bigint DEFAULT nextval('application_usecase_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "author" character varying(255),
    "beneficiary" character varying(255),
    "platform" character varying(255),
    "slug" character varying(255),
    "status" character varying(255),
    "url" character varying(255),
    "uuid" character(36),
    "user_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "comment" text,
    "description" text,
    "imageuuid" character(36),
    CONSTRAINT "idx_696636_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696636_uk11k3vo4kqen1xhwxwcxyxthap" UNIQUE ("slug"),
    CONSTRAINT "idx_696636_ukgcp2cvir5gv395nj4aaunob9g" UNIQUE ("uuid")
) WITH (oids = false);

CREATE INDEX "idx_696636_fkjqp9nx7dqbaun7xvfo1e8amsr" ON "public"."application_usecase" USING btree ("user_id");


DROP TABLE IF EXISTS "application_usecase_dataset_ids";
CREATE TABLE "public"."application_usecase_dataset_ids" (
    "application_usecase_id" bigint NOT NULL,
    "dataset_ids" bigint
) WITH (oids = false);

CREATE INDEX "idx_696642_fkotc3v5m7qi13gdgb8octwnhns" ON "public"."application_usecase_dataset_ids" USING btree ("application_usecase_id");


DROP TABLE IF EXISTS "catalog";
DROP SEQUENCE IF EXISTS catalog_id_seq;
CREATE SEQUENCE catalog_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."catalog" (
    "id" bigint DEFAULT nextval('catalog_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "identifier" character varying(255),
    "slug" character varying(255),
    "title" text,
    "licence_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "title_en" text,
    CONSTRAINT "idx_696646_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696646_ukfonoj8vppd708rn65xeusruvf" UNIQUE ("slug"),
    CONSTRAINT "idx_696646_ukn8gavaatg2qytb65skfd278ai" UNIQUE ("identifier")
) WITH (oids = false);

CREATE INDEX "idx_696646_fkne4ved9e7hb0s67yuxkwbyxvh" ON "public"."catalog" USING btree ("licence_id");


DROP TABLE IF EXISTS "category";
DROP SEQUENCE IF EXISTS category_id_seq;
CREATE SEQUENCE category_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."category" (
    "id" bigint DEFAULT nextval('category_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "featured" boolean NOT NULL,
    "icon" character varying(255),
    "parent_id" bigint,
    "title" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    "edp_title" character varying(255),
    "title_en" character varying(255),
    CONSTRAINT "idx_696653_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "cms_attachment";
DROP SEQUENCE IF EXISTS cms_attachment_id_seq;
CREATE SEQUENCE cms_attachment_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."cms_attachment" (
    "id" bigint DEFAULT nextval('cms_attachment_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "file_data" bytea,
    "filename" character varying(255),
    "mime_type" character varying(255),
    "cms_page_id" bigint,
    CONSTRAINT "idx_696660_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696660_fkd24jc8oag6itrip826odio0d" ON "public"."cms_attachment" USING btree ("cms_page_id");


DROP TABLE IF EXISTS "cms_menu_item";
DROP SEQUENCE IF EXISTS cms_menu_item_id_seq;
CREATE SEQUENCE cms_menu_item_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."cms_menu_item" (
    "id" bigint DEFAULT nextval('cms_menu_item_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    CONSTRAINT "idx_696667_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "comment";
DROP SEQUENCE IF EXISTS comment_id_seq;
CREATE SEQUENCE comment_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."comment" (
    "id" bigint DEFAULT nextval('comment_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "author_id" bigint,
    "author_name" character varying(255),
    "body" text,
    "dataset_id" bigint,
    "deleted" boolean,
    "deleted_date" timestamptz,
    "ip_address" character varying(255),
    "parent_id" bigint,
    "request_id" bigint,
    "deleted_on" timestamptz,
    "dataset_uuid" character varying(255),
    CONSTRAINT "idx_696672_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "css_rule_override";
DROP SEQUENCE IF EXISTS css_rule_override_id_seq;
CREATE SEQUENCE css_rule_override_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."css_rule_override" (
    "id" bigint DEFAULT nextval('css_rule_override_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "active" boolean,
    "css_order" bigint,
    "css_override" text,
    "expires" timestamptz,
    "title" text,
    CONSTRAINT "idx_696679_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "dataset";
DROP SEQUENCE IF EXISTS dataset_id_seq;
CREATE SEQUENCE dataset_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset" (
    "id" bigint DEFAULT nextval('dataset_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "catalog_id" bigint,
    "category_old" character varying(255),
    "coordinator_id" bigint,
    "description" text,
    "financed" boolean,
    "financing_plan_id" bigint,
    "financing_priorities" text,
    "financing_received" bigint,
    "financing_required" bigint,
    "internal_id" character varying(255),
    "is_public" boolean,
    "language" character varying(255),
    "licence_id" bigint,
    "meta" text,
    "organization_id" bigint,
    "origin" character varying(255),
    "priority_score" bigint,
    "published" timestamptz,
    "representative_id" bigint,
    "slug" character varying(255),
    "soft_deleted" timestamptz,
    "spatial_coverage" character varying(255),
    "status" character varying(255),
    "tags" text,
    "temporal_coverage" character varying(255),
    "theme" character varying(255),
    "title" text,
    "update_frequency" character varying(255),
    "uuid" character(36),
    "will_be_financed" boolean NOT NULL,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "catalog" bigint,
    "licence" bigint,
    "access_rights" text,
    "coordinator" bigint,
    "manager_id" bigint,
    "category_id" bigint,
    "distribution_conditions" text,
    "description_en" text,
    "last_update" timestamptz,
    "title_en" text,
    "structure_data" text,
    "structure_filename" character varying(255),
    "notes" text,
    "frequency_id" bigint,
    "current_structure_id" bigint,
    CONSTRAINT "idx_696686_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696686_uk2ujrnxoh8v5arnqre8euk4b4u" UNIQUE ("slug"),
    CONSTRAINT "idx_696686_uk95jpd7a0tb2bhuwsv5dy046mm" UNIQUE ("uuid"),
    CONSTRAINT "idx_696686_ukd7wxd99dbggcgonaqkwk0my32" UNIQUE ("internal_id", "organization_id")
) WITH (oids = false);

CREATE INDEX "idx_696686_fk4k59c9bbvkoab5tcmxuawme2k" ON "public"."dataset" USING btree ("licence");

CREATE INDEX "idx_696686_fkfx0j9c430ywhkw66bwubntd2j" ON "public"."dataset" USING btree ("current_structure_id");

CREATE INDEX "idx_696686_fkh5bnale3qsflk1roluhb5boy6" ON "public"."dataset" USING btree ("category_id");

CREATE INDEX "idx_696686_fkk54wag0yfnoycq9r3y987cxe9" ON "public"."dataset" USING btree ("frequency_id");

CREATE INDEX "idx_696686_fkm7p6euln7a9mtx3gq7tyypcs0" ON "public"."dataset" USING btree ("coordinator");

CREATE INDEX "idx_696686_fkn1j40hydq7lndf33pob9o9iql" ON "public"."dataset" USING btree ("manager_id");

CREATE INDEX "idx_696686_fkppoqdno4w41s70hdov9v984wl" ON "public"."dataset" USING btree ("catalog");


DROP TABLE IF EXISTS "dataset_distribution";
DROP SEQUENCE IF EXISTS dataset_distribution_id_seq;
CREATE SEQUENCE dataset_distribution_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_distribution" (
    "id" bigint DEFAULT nextval('dataset_distribution_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "distribution_version" bigint,
    "filename" character varying(255),
    "identifier" character varying(255),
    "issued" character varying(255),
    "mime_type" character varying(255),
    "municipality" character varying(255),
    "period_end" character varying(255),
    "period_start" character varying(255),
    "region" character varying(255),
    "size" bigint,
    "title" text,
    "type" character varying(255),
    "url" text,
    "dataset_id" bigint,
    "comment" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "url_format_id" bigint,
    "access_url" character varying(255),
    CONSTRAINT "idx_696693_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696693_fkexb2irkqg90qyai7dwkg1g3yj" ON "public"."dataset_distribution" USING btree ("dataset_id");

CREATE INDEX "idx_696693_fkomy7mq25j3xlxp4jowvmat7d4" ON "public"."dataset_distribution" USING btree ("url_format_id");


DROP TABLE IF EXISTS "dataset_event";
DROP SEQUENCE IF EXISTS dataset_event_id_seq;
CREATE SEQUENCE dataset_event_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_event" (
    "id" bigint DEFAULT nextval('dataset_event_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "dataset_id" bigint,
    "details" character varying(255),
    "status" character varying(255),
    "type" character varying(255),
    "user" bytea,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "user_id" bigint,
    CONSTRAINT "idx_696700_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696700_fkofdfglrgk9uep05wog6x0xcw" ON "public"."dataset_event" USING btree ("user_id");


DROP TABLE IF EXISTS "dataset_migrate";
DROP SEQUENCE IF EXISTS dataset_migrate_id_seq;
CREATE SEQUENCE dataset_migrate_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_migrate" (
    "id" bigint DEFAULT nextval('dataset_migrate_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "catalog_id" bigint,
    "category" character varying(255),
    "description" text,
    "licence_id" bigint,
    "organization_id" bigint,
    "representative_id" bigint,
    "tags" text,
    "theme" character varying(255),
    "title" text,
    "version" bigint NOT NULL,
    "update_frequency" character varying(255),
    "internal_id" character varying(255),
    "origin" character varying(255),
    "published" timestamptz,
    "language" character varying(255),
    "temporal_coverage" character varying(255),
    "spatial_coverage" character varying(255),
    "is_public" boolean,
    "meta" text,
    "coordinator_id" bigint,
    "financed" boolean,
    "financing_plan_id" bigint,
    "financing_priorities" text,
    "financing_received" bigint,
    "financing_required" bigint,
    "priority_score" bigint,
    "slug" character varying(255),
    "soft_deleted" timestamptz,
    "status" character varying(255),
    "uuid" character(36),
    "will_be_financed" boolean NOT NULL,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696707_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696707_uk95jpd7a0tb2bhuwsv5dy046mm" UNIQUE ("uuid")
) WITH (oids = false);


DROP TABLE IF EXISTS "dataset_remark";
DROP SEQUENCE IF EXISTS dataset_remark_id_seq;
CREATE SEQUENCE dataset_remark_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_remark" (
    "id" bigint DEFAULT nextval('dataset_remark_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "body" text,
    "author_id" bigint,
    "dataset_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696714_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696714_fkb787tufhteyfo5l43abdlj46r" ON "public"."dataset_remark" USING btree ("author_id");

CREATE INDEX "idx_696714_fkdf213wga71ph9g7uea9bc1cv6" ON "public"."dataset_remark" USING btree ("dataset_id");


DROP TABLE IF EXISTS "dataset_resource";
DROP SEQUENCE IF EXISTS dataset_resource_id_seq;
CREATE SEQUENCE dataset_resource_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_resource" (
    "id" bigint DEFAULT nextval('dataset_resource_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "data" bytea,
    "dataset_id" bigint,
    "description" text,
    "filename" text,
    "issued" character varying(255),
    "mime" text,
    "rating" bigint,
    "size" bigint,
    "spatial_coverage" character varying(255),
    "temporal_coverage" character varying(255),
    "title" character varying(255),
    "type" character varying(255),
    "url" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696721_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "dataset_resource_migrate";
DROP SEQUENCE IF EXISTS dataset_resource_migrate_id_seq;
CREATE SEQUENCE dataset_resource_migrate_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_resource_migrate" (
    "id" bigint DEFAULT nextval('dataset_resource_migrate_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "data" bytea,
    "dataset_id" bigint,
    "filename" text,
    "mime" text,
    "rating" bigint,
    "size" bigint,
    "type" character varying(255),
    "url" text,
    "version" bigint NOT NULL,
    "description" text,
    "temporal" character varying(255),
    "title" character varying(255),
    "spatial" character varying(255),
    "spatial_coverage" character varying(255),
    "temporal_coverage" character varying(255),
    "issued" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696728_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "dataset_structure";
DROP SEQUENCE IF EXISTS dataset_structure_id_seq;
CREATE SEQUENCE dataset_structure_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_structure" (
    "id" bigint DEFAULT nextval('dataset_structure_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "distribution_version" bigint,
    "filename" character varying(255),
    "identifier" character varying(255),
    "mime_type" character varying(255),
    "size" bigint,
    "title" text,
    "dataset_id" bigint,
    "standardized" boolean,
    CONSTRAINT "idx_696735_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696735_fk2v2vvx2loa3lbico9oey4stsj" ON "public"."dataset_structure" USING btree ("dataset_id");


DROP TABLE IF EXISTS "dataset_structure_field";
DROP SEQUENCE IF EXISTS dataset_structure_field_id_seq;
CREATE SEQUENCE dataset_structure_field_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_structure_field" (
    "id" bigint DEFAULT nextval('dataset_structure_field_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "data_title" character varying(255),
    "db_table_name" character varying(255),
    "order_id" bigint NOT NULL,
    "scheme" character varying(255),
    "standard_title" character varying(255),
    "technical_title" character varying(255),
    "type" character varying(255),
    "dataset_id" bigint,
    CONSTRAINT "idx_696742_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696742_fk8w1tjayu0ut13h9g7f8f6ryqd" ON "public"."dataset_structure_field" USING btree ("dataset_id");


DROP TABLE IF EXISTS "dataset_visit";
DROP SEQUENCE IF EXISTS dataset_visit_id_seq;
CREATE SEQUENCE dataset_visit_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."dataset_visit" (
    "id" bigint DEFAULT nextval('dataset_visit_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "last_visited" timestamptz,
    "visit_count" bigint NOT NULL,
    "dataset_id" bigint,
    CONSTRAINT "idx_696749_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696749_fk5enxj7egeon3u4arv6t8hr8lf" ON "public"."dataset_visit" USING btree ("dataset_id");


DROP TABLE IF EXISTS "distribution_format";
DROP SEQUENCE IF EXISTS distribution_format_id_seq;
CREATE SEQUENCE distribution_format_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."distribution_format" (
    "id" bigint DEFAULT nextval('distribution_format_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "title" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696754_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "email_template";
DROP SEQUENCE IF EXISTS email_template_id_seq;
CREATE SEQUENCE email_template_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."email_template" (
    "id" bigint DEFAULT nextval('email_template_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "identifier" character varying(255),
    "template" text,
    "variables" text,
    "subject" text,
    "title" text,
    CONSTRAINT "idx_696759_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696759_uk5bc0ddajl6jdbstkwabi2n092" UNIQUE ("identifier")
) WITH (oids = false);


DROP TABLE IF EXISTS "external_site";
DROP SEQUENCE IF EXISTS external_site_id_seq;
CREATE SEQUENCE external_site_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."external_site" (
    "id" bigint DEFAULT nextval('external_site_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "imageuuid" character(36),
    "title" text,
    "type" character varying(255),
    "url" character varying(255),
    CONSTRAINT "idx_696766_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "faq";
DROP SEQUENCE IF EXISTS faq_id_seq;
CREATE SEQUENCE faq_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."faq" (
    "id" bigint DEFAULT nextval('faq_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "answer" text,
    "question" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696773_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "file_resource";
DROP SEQUENCE IF EXISTS file_resource_id_seq;
CREATE SEQUENCE file_resource_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."file_resource" (
    "id" bigint DEFAULT nextval('file_resource_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "filename" character varying(255),
    "identifier" character(36),
    "mime_type" character varying(255),
    "obj_class" character varying(255),
    "obj_id" bigint,
    "size" bigint,
    "type" bigint,
    CONSTRAINT "idx_696780_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "financing_plan";
DROP SEQUENCE IF EXISTS financing_plan_id_seq;
CREATE SEQUENCE financing_plan_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."financing_plan" (
    "id" bigint DEFAULT nextval('financing_plan_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "financed_datasets" bigint,
    "financing_plan_state_id" bigint,
    "projected_cost" bigint,
    "projected_datasets" bigint,
    "received_financing" bigint,
    "status" character varying(255),
    "year" bigint,
    "created_by" bigint,
    "organization_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696787_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696787_ukek9xiakdr85a16q9yhwbg5sax" UNIQUE ("organization_id", "year")
) WITH (oids = false);

CREATE INDEX "idx_696787_fkrue1sug7ymabvpx58i6mcf3ux" ON "public"."financing_plan" USING btree ("created_by");

COMMENT ON TABLE "public"."financing_plan" IS 'Organization dataset financing plan by year';


DROP TABLE IF EXISTS "financing_plan_state";
DROP SEQUENCE IF EXISTS financing_plan_state_id_seq;
CREATE SEQUENCE financing_plan_state_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."financing_plan_state" (
    "id" bigint DEFAULT nextval('financing_plan_state_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "details" text,
    "financing_plan_id" bigint,
    "status" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696792_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "format";
DROP SEQUENCE IF EXISTS format_id_seq;
CREATE SEQUENCE format_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."format" (
    "id" bigint DEFAULT nextval('format_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "extension" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "mimetype" text,
    "rating" bigint,
    "title" character varying(255),
    CONSTRAINT "idx_696799_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "frequency";
DROP SEQUENCE IF EXISTS frequency_id_seq;
CREATE SEQUENCE frequency_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."frequency" (
    "id" bigint DEFAULT nextval('frequency_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "title" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "title_en" text,
    "uri" character varying(255),
    CONSTRAINT "idx_696806_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "geoportal_lt_entry";
DROP SEQUENCE IF EXISTS geoportal_lt_entry_id_seq;
CREATE SEQUENCE geoportal_lt_entry_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."geoportal_lt_entry" (
    "id" bigint DEFAULT nextval('geoportal_lt_entry_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "raw_data" text,
    "type" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696813_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "global_email";
DROP SEQUENCE IF EXISTS global_email_id_seq;
CREATE SEQUENCE global_email_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."global_email" (
    "id" bigint DEFAULT nextval('global_email_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "body" text,
    "title" character varying(255),
    CONSTRAINT "idx_696820_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "harvested_visit";
DROP SEQUENCE IF EXISTS harvested_visit_id_seq;
CREATE SEQUENCE harvested_visit_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."harvested_visit" (
    "id" bigint DEFAULT nextval('harvested_visit_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "last_visited" timestamptz,
    "visit_count" bigint NOT NULL,
    "harvesting_result_id" bigint,
    CONSTRAINT "idx_696827_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696827_fk4vif4qkrtl19dsxwnii9i0909" ON "public"."harvested_visit" USING btree ("harvesting_result_id");


DROP TABLE IF EXISTS "harvesting_job";
DROP SEQUENCE IF EXISTS harvesting_job_id_seq;
CREATE SEQUENCE harvesting_job_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."harvesting_job" (
    "id" bigint DEFAULT nextval('harvesting_job_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "indexed" boolean,
    "schedule" character varying(255),
    "started" timestamptz,
    "stopped" timestamptz,
    "title" character varying(255),
    "translated" boolean,
    "type" character varying(255),
    "url" character varying(255),
    "organization" bigint,
    "active" boolean,
    CONSTRAINT "idx_696832_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696832_fk2ryi0ker86i5vc5f9p48w64wt" ON "public"."harvesting_job" USING btree ("organization");


DROP TABLE IF EXISTS "harvesting_result";
DROP SEQUENCE IF EXISTS harvesting_result_id_seq;
CREATE SEQUENCE harvesting_result_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."harvesting_result" (
    "published" boolean NOT NULL,
    "id" bigint DEFAULT nextval('harvesting_result_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "remote_id" character varying(255),
    "title" text,
    "job_id" bigint,
    "description_en" text,
    "keywords" text,
    "organization" text,
    "raw_data" text,
    "title_en" text,
    "category_id" bigint,
    CONSTRAINT "idx_696839_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696839_fk_harv_result_category" ON "public"."harvesting_result" USING btree ("category_id");

CREATE INDEX "idx_696839_fk_harv_result_harv_job" ON "public"."harvesting_result" USING btree ("job_id");


DROP TABLE IF EXISTS "learning_material";
DROP SEQUENCE IF EXISTS learning_material_id_seq;
CREATE SEQUENCE learning_material_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."learning_material" (
    "id" bigint DEFAULT nextval('learning_material_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "comment" text,
    "description" text,
    "learning_material_id" bigint,
    "status" character varying(255),
    "topic" character varying(255),
    "user_id" bigint,
    "video_url" character varying(255),
    "imageuuid" character(36),
    "summary" text,
    "author_name" text,
    "published" date,
    "uuid" character(36),
    "requested" boolean DEFAULT false,
    CONSTRAINT "idx_696846_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696846_ukqu11paplkqkt2hyre1e2syjgt" UNIQUE ("uuid")
) WITH (oids = false);

CREATE INDEX "idx_696846_fk67j6xkiixutc3kaxwshn3kd8u" ON "public"."learning_material" USING btree ("user_id");


DROP TABLE IF EXISTS "licence";
DROP SEQUENCE IF EXISTS licence_id_seq;
CREATE SEQUENCE licence_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."licence" (
    "id" bigint DEFAULT nextval('licence_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "identifier" character varying(255),
    "title" character varying(255),
    "url" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696854_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696854_uk1st8clbrf69hv9gl2nhfm0myw" UNIQUE ("identifier"),
    CONSTRAINT "idx_696854_uk_1st8clbrf69hv9gl2nhfm0myw" UNIQUE ("identifier")
) WITH (oids = false);


DROP TABLE IF EXISTS "municipality";
DROP SEQUENCE IF EXISTS municipality_id_seq;
CREATE SEQUENCE municipality_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."municipality" (
    "id" bigint DEFAULT nextval('municipality_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "title" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696861_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "national_financing_plan";
DROP SEQUENCE IF EXISTS national_financing_plan_id_seq;
CREATE SEQUENCE national_financing_plan_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."national_financing_plan" (
    "id" bigint DEFAULT nextval('national_financing_plan_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "confirmation_date" timestamptz,
    "confirmed" boolean,
    "confirmed_budget" bigint,
    "confirmed_by" bigint,
    "estimated_budget" bigint,
    "year" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696868_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696868_ukakpi5bggg3ngiv2l1yocswuwy" UNIQUE ("year")
) WITH (oids = false);


DROP TABLE IF EXISTS "news_item";
DROP SEQUENCE IF EXISTS news_item_id_seq;
CREATE SEQUENCE news_item_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."news_item" (
    "id" bigint DEFAULT nextval('news_item_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "author" bytea,
    "body" text,
    "slug" character varying(255),
    "tags" character varying(255),
    "title" text,
    "uuid" character(36),
    "deleted" boolean,
    "deleted_on" timestamptz,
    "user_id" bigint,
    "imageuuid" character(36),
    "summary" text,
    "author_name" text,
    "is_public" boolean,
    "published" date,
    CONSTRAINT "idx_696878_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696878_uk511y70m0jr63davomeikaxo7v" UNIQUE ("slug"),
    CONSTRAINT "idx_696878_uk6afehd75fw4450ewl63mpmclk" UNIQUE ("uuid")
) WITH (oids = false);

CREATE INDEX "idx_696878_fk2bn8yor8clqe8rr80sc4uwqyn" ON "public"."news_item" USING btree ("user_id");


DROP TABLE IF EXISTS "newsletter_subscription";
DROP SEQUENCE IF EXISTS newsletter_subscription_id_seq;
CREATE SEQUENCE newsletter_subscription_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."newsletter_subscription" (
    "id" bigint DEFAULT nextval('newsletter_subscription_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "email" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    "is_active" boolean NOT NULL,
    CONSTRAINT "idx_696873_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "old_password";
DROP SEQUENCE IF EXISTS old_password_id_seq;
CREATE SEQUENCE old_password_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."old_password" (
    "id" bigint DEFAULT nextval('old_password_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "password" character(60),
    "user_id" bigint,
    CONSTRAINT "idx_696885_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696885_fk3h975gamp3cdbn09ljckuiv3a" ON "public"."old_password" USING btree ("user_id");


DROP TABLE IF EXISTS "open_data_gov_lt_entry";
DROP SEQUENCE IF EXISTS open_data_gov_lt_entry_id_seq;
CREATE SEQUENCE open_data_gov_lt_entry_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."open_data_gov_lt_entry" (
    "id" bigint DEFAULT nextval('open_data_gov_lt_entry_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "alt_title" text,
    "code" text,
    "contact_info" text,
    "data_extent" text,
    "data_trustworthiness" text,
    "dataset_begins" text,
    "dataset_conditions" text,
    "dataset_ends" text,
    "dataset_type" text,
    "date_meta_published" text,
    "description" text,
    "format" text,
    "keywords" text,
    "publisher" text,
    "refresh_period" text,
    "title" text,
    "topic" text,
    "url" text,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696890_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "organization";
DROP SEQUENCE IF EXISTS organization_id_seq;
CREATE SEQUENCE organization_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."organization" (
    "id" bigint DEFAULT nextval('organization_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "municipality" character varying(255),
    "region" character varying(255),
    "slug" character varying(255),
    "title" text,
    "uuid" character(36),
    "deleted" boolean,
    "deleted_on" timestamptz,
    "address" character varying(255),
    "company_code" character varying(255),
    "email" character varying(255),
    "is_public" boolean,
    "phone" character varying(255),
    "jurisdiction" character varying(255),
    "website" character varying(255),
    "imageuuid" character(36),
    CONSTRAINT "idx_696897_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696897_ukh2su5s2veeq84vjfeb4s87tep" UNIQUE ("slug"),
    CONSTRAINT "idx_696897_uks9xj0yg0stek0h7hedcn2qro3" UNIQUE ("uuid")
) WITH (oids = false);


DROP TABLE IF EXISTS "partner_application";
DROP SEQUENCE IF EXISTS partner_application_id_seq;
CREATE SEQUENCE partner_application_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."partner_application" (
    "id" bigint DEFAULT nextval('partner_application_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "email" text,
    "filename" text,
    "letter" bytea,
    "organization_title" text,
    "phone" text,
    "viisp_email" character varying(255),
    "viisp_first_name" character varying(255),
    "viisp_last_name" character varying(255),
    "viisp_phone" character varying(255),
    "comment" text,
    "status" character varying(255),
    "viisp_dob" character varying(255),
    CONSTRAINT "idx_696904_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "password_reset_token";
DROP SEQUENCE IF EXISTS password_reset_token_id_seq;
CREATE SEQUENCE password_reset_token_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."password_reset_token" (
    "id" bigint DEFAULT nextval('password_reset_token_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "expiry_date" timestamptz,
    "token" character varying(255),
    "user_id" bigint NOT NULL,
    "used_date" timestamptz,
    CONSTRAINT "idx_696911_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696911_fk5lwtbncug84d4ero33v3cfxvl" ON "public"."password_reset_token" USING btree ("user_id");


DROP TABLE IF EXISTS "published_report";
DROP SEQUENCE IF EXISTS published_report_id_seq;
CREATE SEQUENCE published_report_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."published_report" (
    "id" bigint DEFAULT nextval('published_report_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "data" text,
    "title" text,
    CONSTRAINT "idx_696916_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "region";
DROP SEQUENCE IF EXISTS region_id_seq;
CREATE SEQUENCE region_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."region" (
    "id" bigint DEFAULT nextval('region_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "title" text,
    CONSTRAINT "idx_696923_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "report";
DROP SEQUENCE IF EXISTS report_id_seq;
CREATE SEQUENCE report_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."report" (
    "id" bigint DEFAULT nextval('report_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "body" character varying(255),
    "name" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696930_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "representative";
DROP SEQUENCE IF EXISTS representative_id_seq;
CREATE SEQUENCE representative_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."representative" (
    "id" bigint DEFAULT nextval('representative_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "email" character varying(255),
    "first_name" character varying(255),
    "last_name" character varying(255),
    "organization_id" bigint,
    "phone" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696937_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "request";
DROP SEQUENCE IF EXISTS request_id_seq;
CREATE SEQUENCE request_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."request" (
    "id" bigint DEFAULT nextval('request_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "comment" text,
    "dataset_id" bigint,
    "description" text,
    "format" character varying(255),
    "is_existing" boolean NOT NULL,
    "notes" text,
    "organization_id" bigint,
    "periodicity" character varying(255),
    "planned_opening_date" date,
    "purpose" character varying(255),
    "slug" character varying(255),
    "status" character varying(255),
    "title" character varying(255),
    "uuid" character(36),
    "user_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "changes" character varying(255),
    "is_public" boolean NOT NULL,
    "structure_data" text,
    "structure_filename" character varying(255),
    CONSTRAINT "idx_696944_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696944_uk6dgywmcxa5qo4onrx95vxe5hf" UNIQUE ("slug"),
    CONSTRAINT "idx_696944_ukopq611dvscynyvfpgpbvig29v" UNIQUE ("uuid")
) WITH (oids = false);

CREATE INDEX "idx_696944_fkqws2fdeknk90txm7qnm9bxd07" ON "public"."request" USING btree ("user_id");


DROP TABLE IF EXISTS "request_event";
DROP SEQUENCE IF EXISTS request_event_id_seq;
CREATE SEQUENCE request_event_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."request_event" (
    "id" bigint DEFAULT nextval('request_event_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "comment" text,
    "meta" text,
    "type" character varying(255),
    "request_id" bigint,
    CONSTRAINT "idx_696951_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_696951_fkboyhtgld73e9xslhlemxax5n" ON "public"."request_event" USING btree ("request_id");


DROP TABLE IF EXISTS "request_structure";
DROP SEQUENCE IF EXISTS request_structure_id_seq;
CREATE SEQUENCE request_structure_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."request_structure" (
    "id" bigint DEFAULT nextval('request_structure_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "data_notes" character varying(255),
    "data_title" character varying(255),
    "data_type" character varying(255),
    "dictionary_title" character varying(255),
    "request_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    CONSTRAINT "idx_696958_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "sent_mail";
DROP SEQUENCE IF EXISTS sent_mail_id_seq;
CREATE SEQUENCE sent_mail_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."sent_mail" (
    "id" bigint DEFAULT nextval('sent_mail_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "recipient" character varying(255),
    CONSTRAINT "idx_696965_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "sso_token";
DROP SEQUENCE IF EXISTS sso_token_id_seq;
CREATE SEQUENCE sso_token_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."sso_token" (
    "id" bigint DEFAULT nextval('sso_token_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "ip" character varying(255),
    "token" character varying(36),
    "user_id" bigint,
    CONSTRAINT "idx_696970_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696970_ukbf4iv8dfxpwfmh5e2xupfqqsa" UNIQUE ("token")
) WITH (oids = false);

CREATE INDEX "idx_696970_fkkju7shggmw61xqmyw2ha2u6hn" ON "public"."sso_token" USING btree ("user_id");


DROP TABLE IF EXISTS "suggestion";
DROP SEQUENCE IF EXISTS suggestion_id_seq;
CREATE SEQUENCE suggestion_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."suggestion" (
    "id" bigint DEFAULT nextval('suggestion_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "body" text,
    "name" character varying(255),
    "deleted" boolean,
    "deleted_on" timestamptz,
    "email" text,
    CONSTRAINT "idx_696975_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "terms_of_use";
DROP SEQUENCE IF EXISTS terms_of_use_id_seq;
CREATE SEQUENCE terms_of_use_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."terms_of_use" (
    "id" bigint DEFAULT nextval('terms_of_use_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "description" text,
    "file" character varying(255),
    "title" character varying(255),
    "body" text,
    "imageuuid" character(36),
    "published" date,
    CONSTRAINT "idx_696982_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "usecase";
DROP SEQUENCE IF EXISTS usecase_id_seq;
CREATE SEQUENCE usecase_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."usecase" (
    "id" bigint DEFAULT nextval('usecase_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "beneficiary_group" character varying(255),
    "benefit" text,
    "description" text,
    "extra_information" text,
    "slug" character varying(255),
    "status" character varying(255),
    "url" character varying(255),
    "uuid" character(36),
    "user_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "comment" text,
    "imageuuid" character(36),
    CONSTRAINT "idx_696989_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_696989_uk1oeiv5hog092d0ogeb8ra7nig" UNIQUE ("slug"),
    CONSTRAINT "idx_696989_ukfqd3n77pj91v0j47gl6adkyo1" UNIQUE ("uuid")
) WITH (oids = false);

CREATE INDEX "idx_696989_fku1uqn07hiom0uhv2fg22d6ou" ON "public"."usecase" USING btree ("user_id");


DROP TABLE IF EXISTS "usecase_dataset_ids";
CREATE TABLE "public"."usecase_dataset_ids" (
    "id" bigint DEFAULT nextval('usecase_dataset_ids_id_seq') NOT NULL,
    "usecase_id" bigint NOT NULL,
    "dataset_ids" bigint
) WITH (oids = false);

CREATE INDEX "idx_696995_fkjojfec74pegtfn2xre9ycrkgn" ON "public"."usecase_dataset_ids" USING btree ("usecase_id");


DROP TABLE IF EXISTS "usecase_like";
DROP SEQUENCE IF EXISTS usecase_like_id_seq;
CREATE SEQUENCE usecase_like_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."usecase_like" (
    "id" bigint DEFAULT nextval('usecase_like_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "usecase_uuid" character varying(255),
    "user_id" bigint,
    CONSTRAINT "idx_696999_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "user";
DROP SEQUENCE IF EXISTS user_id_seq;
CREATE SEQUENCE user_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."user" (
    "id" bigint DEFAULT nextval('user_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "email" character varying(255),
    "first_name" character varying(255),
    "last_login" timestamptz,
    "last_name" character varying(255),
    "password" character(60),
    "role" character varying(255),
    "organization_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "phone" character varying(255),
    "needs_password_change" boolean NOT NULL,
    "year_of_birth" bigint,
    "disabled" boolean NOT NULL,
    "suspended" boolean NOT NULL,
    CONSTRAINT "idx_697004_primary" PRIMARY KEY ("id"),
    CONSTRAINT "idx_697004_uk_ob8kqyqqgmefl0aco34akdtpe" UNIQUE ("email"),
    CONSTRAINT "idx_697004_ukob8kqyqqgmefl0aco34akdtpe" UNIQUE ("email")
) WITH (oids = false);

CREATE INDEX "idx_697004_fki3ynrf4qjomj2hdjx7ssa3mlh" ON "public"."user" USING btree ("organization_id");

COMMENT ON TABLE "public"."user" IS 'ADP user of any kind';


DROP TABLE IF EXISTS "user_dataset_subscription";
DROP SEQUENCE IF EXISTS user_dataset_subscription_id_seq;
CREATE SEQUENCE user_dataset_subscription_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."user_dataset_subscription" (
    "id" bigint DEFAULT nextval('user_dataset_subscription_id_seq') NOT NULL,
    "created" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "dataset_id" bigint,
    "user_id" bigint,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "dataset" bigint,
    "user" bigint,
    "active" boolean NOT NULL,
    CONSTRAINT "idx_697011_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_697011_fkfuokd2v3s9sdobtggqtiuxjog" ON "public"."user_dataset_subscription" USING btree ("dataset");

CREATE INDEX "idx_697011_fkpbl2oik54h31p0fyq4n72wetv" ON "public"."user_dataset_subscription" USING btree ("user");


DROP TABLE IF EXISTS "user_like";
DROP SEQUENCE IF EXISTS user_like_id_seq;
CREATE SEQUENCE user_like_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."user_like" (
    "id" bigint DEFAULT nextval('user_like_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "request_id" bigint,
    "user_id" bigint,
    CONSTRAINT "idx_697016_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "user_table_preferences";
DROP SEQUENCE IF EXISTS user_table_preferences_id_seq;
CREATE SEQUENCE user_table_preferences_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."user_table_preferences" (
    "id" bigint DEFAULT nextval('user_table_preferences_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "table_column_string" text,
    "table_id" character varying(255),
    "user_id" bigint,
    CONSTRAINT "idx_697021_primary" PRIMARY KEY ("id")
) WITH (oids = false);


DROP TABLE IF EXISTS "user_vote";
DROP SEQUENCE IF EXISTS user_vote_id_seq;
CREATE SEQUENCE user_vote_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1;

CREATE TABLE "public"."user_vote" (
    "id" bigint DEFAULT nextval('user_vote_id_seq') NOT NULL,
    "created" timestamptz,
    "deleted" boolean,
    "deleted_on" timestamptz,
    "modified" timestamptz,
    "version" bigint NOT NULL,
    "rating" bigint NOT NULL,
    "dataset_id" bigint,
    "user_id" bigint,
    "harvested_id" bigint,
    CONSTRAINT "idx_697028_primary" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "idx_697028_fk2q50phs57njg6g0qvha1r8703" ON "public"."user_vote" USING btree ("user_id");

CREATE INDEX "idx_697028_fkmaho12gli2m957igj2bxsu7o0" ON "public"."user_vote" USING btree ("harvested_id");

CREATE INDEX "idx_697028_fkq0c0k0uxbtdrldpfdtlq1jai7" ON "public"."user_vote" USING btree ("dataset_id");


ALTER TABLE ONLY "public"."adp_cms_page" ADD CONSTRAINT "fkh6y4ejn6r1yjtr6v8sa80u57p" FOREIGN KEY (parent_id) REFERENCES adp_cms_page(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."api_key" ADD CONSTRAINT "fk2cifbfne14e6w1in2bjbs6sf6" FOREIGN KEY (organization_id) REFERENCES organization(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."application_usecase" ADD CONSTRAINT "fkjqp9nx7dqbaun7xvfo1e8amsr" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."application_usecase_dataset_ids" ADD CONSTRAINT "fkotc3v5m7qi13gdgb8octwnhns" FOREIGN KEY (application_usecase_id) REFERENCES application_usecase(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."catalog" ADD CONSTRAINT "fkne4ved9e7hb0s67yuxkwbyxvh" FOREIGN KEY (licence_id) REFERENCES licence(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."cms_attachment" ADD CONSTRAINT "fkd24jc8oag6itrip826odio0d" FOREIGN KEY (cms_page_id) REFERENCES adp_cms_page(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fk4k59c9bbvkoab5tcmxuawme2k" FOREIGN KEY (licence) REFERENCES licence(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkfx0j9c430ywhkw66bwubntd2j" FOREIGN KEY (current_structure_id) REFERENCES dataset_structure(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkh5bnale3qsflk1roluhb5boy6" FOREIGN KEY (category_id) REFERENCES category(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkk54wag0yfnoycq9r3y987cxe9" FOREIGN KEY (frequency_id) REFERENCES frequency(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkm7p6euln7a9mtx3gq7tyypcs0" FOREIGN KEY (coordinator) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkn1j40hydq7lndf33pob9o9iql" FOREIGN KEY (manager_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset" ADD CONSTRAINT "fkppoqdno4w41s70hdov9v984wl" FOREIGN KEY (catalog) REFERENCES catalog(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_distribution" ADD CONSTRAINT "fkexb2irkqg90qyai7dwkg1g3yj" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset_distribution" ADD CONSTRAINT "fkomy7mq25j3xlxp4jowvmat7d4" FOREIGN KEY (url_format_id) REFERENCES format(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_event" ADD CONSTRAINT "fkofdfglrgk9uep05wog6x0xcw" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_remark" ADD CONSTRAINT "fkb787tufhteyfo5l43abdlj46r" FOREIGN KEY (author_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."dataset_remark" ADD CONSTRAINT "fkdf213wga71ph9g7uea9bc1cv6" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_structure" ADD CONSTRAINT "fk2v2vvx2loa3lbico9oey4stsj" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_structure_field" ADD CONSTRAINT "fk8w1tjayu0ut13h9g7f8f6ryqd" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."dataset_visit" ADD CONSTRAINT "fk5enxj7egeon3u4arv6t8hr8lf" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."financing_plan" ADD CONSTRAINT "fkosf8lm46jp6qbaclte8n7d4s8" FOREIGN KEY (organization_id) REFERENCES organization(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."financing_plan" ADD CONSTRAINT "fkrue1sug7ymabvpx58i6mcf3ux" FOREIGN KEY (created_by) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."harvested_visit" ADD CONSTRAINT "fk4vif4qkrtl19dsxwnii9i0909" FOREIGN KEY (harvesting_result_id) REFERENCES harvesting_result(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."harvesting_job" ADD CONSTRAINT "fk2ryi0ker86i5vc5f9p48w64wt" FOREIGN KEY (organization) REFERENCES organization(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."harvesting_result" ADD CONSTRAINT "fk_harv_result_category" FOREIGN KEY (category_id) REFERENCES category(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."harvesting_result" ADD CONSTRAINT "fk_harv_result_harv_job" FOREIGN KEY (job_id) REFERENCES harvesting_job(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."learning_material" ADD CONSTRAINT "fk67j6xkiixutc3kaxwshn3kd8u" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."news_item" ADD CONSTRAINT "fk2bn8yor8clqe8rr80sc4uwqyn" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."old_password" ADD CONSTRAINT "fk3h975gamp3cdbn09ljckuiv3a" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."password_reset_token" ADD CONSTRAINT "fk5lwtbncug84d4ero33v3cfxvl" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."request" ADD CONSTRAINT "fkqws2fdeknk90txm7qnm9bxd07" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."request_event" ADD CONSTRAINT "fkboyhtgld73e9xslhlemxax5n" FOREIGN KEY (request_id) REFERENCES request(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."sso_token" ADD CONSTRAINT "fkkju7shggmw61xqmyw2ha2u6hn" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."usecase" ADD CONSTRAINT "fku1uqn07hiom0uhv2fg22d6ou" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."usecase_dataset_ids" ADD CONSTRAINT "fkjojfec74pegtfn2xre9ycrkgn" FOREIGN KEY (usecase_id) REFERENCES usecase(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."user" ADD CONSTRAINT "fki3ynrf4qjomj2hdjx7ssa3mlh" FOREIGN KEY (organization_id) REFERENCES organization(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."user_dataset_subscription" ADD CONSTRAINT "fkfuokd2v3s9sdobtggqtiuxjog" FOREIGN KEY (dataset) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."user_dataset_subscription" ADD CONSTRAINT "fkpbl2oik54h31p0fyq4n72wetv" FOREIGN KEY ("user") REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

ALTER TABLE ONLY "public"."user_vote" ADD CONSTRAINT "fk2q50phs57njg6g0qvha1r8703" FOREIGN KEY (user_id) REFERENCES "user"(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."user_vote" ADD CONSTRAINT "fkmaho12gli2m957igj2bxsu7o0" FOREIGN KEY (harvested_id) REFERENCES harvesting_result(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."user_vote" ADD CONSTRAINT "fkq0c0k0uxbtdrldpfdtlq1jai7" FOREIGN KEY (dataset_id) REFERENCES dataset(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

-- 2022-10-21 11:02:32.874979+00

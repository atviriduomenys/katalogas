SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `adp-dev` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_lithuanian_ci */;
USE `adp-dev`;

CREATE TABLE `adp_cms_page` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `page_order` int(11) DEFAULT NULL,
  `published` bit(1) NOT NULL,
  `slug` text COLLATE utf8mb4_lithuanian_ci,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `type` int(11) DEFAULT NULL,
  `parent_id` bigint(20) DEFAULT NULL,
  `language` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `list_children` bit(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `FKh6y4ejn6r1yjtr6v8sa80u57p` (`parent_id`),
  CONSTRAINT `FKh6y4ejn6r1yjtr6v8sa80u57p` FOREIGN KEY (`parent_id`) REFERENCES `adp_cms_page` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `api_description` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `api_version` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `contact_email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `contact_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `contact_url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `desription_html` text COLLATE utf8mb4_lithuanian_ci,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `licence` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `licence_url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `api_key` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `api_key` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `enabled` bit(1) DEFAULT NULL,
  `expires` datetime(6) DEFAULT NULL,
  `organization_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKr6ixjob39jj0hsrmet0wqg14c` (`api_key`),
  KEY `FK2cifbfne14e6w1in2bjbs6sf6` (`organization_id`),
  CONSTRAINT `FK2cifbfne14e6w1in2bjbs6sf6` FOREIGN KEY (`organization_id`) REFERENCES `organization` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `application_setting` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `value` text COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `application_usecase` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `author` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `beneficiary` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `platform` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK11k3vo4kqen1xhwxwcxyxthap` (`slug`),
  UNIQUE KEY `UKgcp2cvir5gv395nj4aaunob9g` (`uuid`),
  KEY `FKjqp9nx7dqbaun7xvfo1e8amsr` (`user_id`),
  CONSTRAINT `FKjqp9nx7dqbaun7xvfo1e8amsr` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `application_usecase_dataset_ids` (
  `application_usecase_id` bigint(20) NOT NULL,
  `dataset_ids` bigint(20) DEFAULT NULL,
  KEY `FKotc3v5m7qi13gdgb8octwnhns` (`application_usecase_id`),
  CONSTRAINT `FKotc3v5m7qi13gdgb8octwnhns` FOREIGN KEY (`application_usecase_id`) REFERENCES `application_usecase` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `catalog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `licence_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `title_en` tinytext COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKn8gavaatg2qytb65skfd278ai` (`identifier`),
  UNIQUE KEY `UKfonoj8vppd708rn65xeusruvf` (`slug`),
  KEY `FKne4ved9e7hb0s67yuxkwbyxvh` (`licence_id`),
  CONSTRAINT `FKne4ved9e7hb0s67yuxkwbyxvh` FOREIGN KEY (`licence_id`) REFERENCES `licence` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `category` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `featured` bit(1) NOT NULL,
  `icon` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `parent_id` bigint(20) DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `edp_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title_en` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `cms_attachment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `file_data` longblob,
  `filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `cms_page_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKd24jc8oag6itrip826odio0d` (`cms_page_id`),
  CONSTRAINT `FKb61y6xtsjm3lph7jvqwvna336` FOREIGN KEY (`cms_page_id`) REFERENCES `cms_page` (`id`),
  CONSTRAINT `FKd24jc8oag6itrip826odio0d` FOREIGN KEY (`cms_page_id`) REFERENCES `adp_cms_page` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `cms_menu_item` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `comment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `author_id` bigint(20) DEFAULT NULL,
  `author_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_date` datetime(6) DEFAULT NULL,
  `ip_address` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `parent_id` bigint(20) DEFAULT NULL,
  `request_id` bigint(20) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `dataset_uuid` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `css_rule_override` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `active` bit(1) DEFAULT NULL,
  `css_order` int(11) DEFAULT NULL,
  `css_override` text COLLATE utf8mb4_lithuanian_ci,
  `expires` datetime(6) DEFAULT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `catalog_id` bigint(20) DEFAULT NULL,
  `category_old` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `coordinator_id` bigint(20) DEFAULT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `financed` bit(1) DEFAULT NULL,
  `financing_plan_id` bigint(20) DEFAULT NULL,
  `financing_priorities` text COLLATE utf8mb4_lithuanian_ci,
  `financing_received` bigint(20) DEFAULT NULL,
  `financing_required` bigint(20) DEFAULT NULL,
  `internal_id` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `is_public` bit(1) DEFAULT NULL,
  `language` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `licence_id` bigint(20) DEFAULT NULL,
  `meta` text COLLATE utf8mb4_lithuanian_ci,
  `organization_id` bigint(20) DEFAULT NULL,
  `origin` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `priority_score` int(11) DEFAULT NULL,
  `published` datetime(6) DEFAULT NULL,
  `representative_id` bigint(20) DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `soft_deleted` datetime(6) DEFAULT NULL,
  `spatial_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `tags` text COLLATE utf8mb4_lithuanian_ci,
  `temporal_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `theme` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `update_frequency` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `will_be_financed` bit(1) NOT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `catalog` bigint(20) DEFAULT NULL,
  `licence` bigint(20) DEFAULT NULL,
  `access_rights` text COLLATE utf8mb4_lithuanian_ci,
  `coordinator` bigint(20) DEFAULT NULL,
  `manager_id` bigint(20) DEFAULT NULL,
  `category_id` bigint(20) DEFAULT NULL,
  `distribution_conditions` text COLLATE utf8mb4_lithuanian_ci,
  `description_en` text COLLATE utf8mb4_lithuanian_ci,
  `last_update` datetime(6) DEFAULT NULL,
  `title_en` text COLLATE utf8mb4_lithuanian_ci,
  `structure_data` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `structure_filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `notes` text COLLATE utf8mb4_lithuanian_ci,
  `frequency_id` bigint(20) DEFAULT NULL,
  `current_structure_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK2ujrnxoh8v5arnqre8euk4b4u` (`slug`),
  UNIQUE KEY `UK95jpd7a0tb2bhuwsv5dy046mm` (`uuid`),
  UNIQUE KEY `UKd7wxd99dbggcgonaqkwk0my32` (`internal_id`,`organization_id`),
  KEY `FKppoqdno4w41s70hdov9v984wl` (`catalog`),
  KEY `FK4k59c9bbvkoab5tcmxuawme2k` (`licence`),
  KEY `FKm7p6euln7a9mtx3gq7tyypcs0` (`coordinator`),
  KEY `FKn1j40hydq7lndf33pob9o9iql` (`manager_id`),
  KEY `FKh5bnale3qsflk1roluhb5boy6` (`category_id`),
  KEY `FKk54wag0yfnoycq9r3y987cxe9` (`frequency_id`),
  KEY `FKfx0j9c430ywhkw66bwubntd2j` (`current_structure_id`),
  CONSTRAINT `FK4k59c9bbvkoab5tcmxuawme2k` FOREIGN KEY (`licence`) REFERENCES `licence` (`id`),
  CONSTRAINT `FKfx0j9c430ywhkw66bwubntd2j` FOREIGN KEY (`current_structure_id`) REFERENCES `dataset_structure` (`id`),
  CONSTRAINT `FKh5bnale3qsflk1roluhb5boy6` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`),
  CONSTRAINT `FKk54wag0yfnoycq9r3y987cxe9` FOREIGN KEY (`frequency_id`) REFERENCES `frequency` (`id`),
  CONSTRAINT `FKm7p6euln7a9mtx3gq7tyypcs0` FOREIGN KEY (`coordinator`) REFERENCES `user` (`id`),
  CONSTRAINT `FKn1j40hydq7lndf33pob9o9iql` FOREIGN KEY (`manager_id`) REFERENCES `user` (`id`),
  CONSTRAINT `FKppoqdno4w41s70hdov9v984wl` FOREIGN KEY (`catalog`) REFERENCES `catalog` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_distribution` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `distribution_version` int(11) DEFAULT NULL,
  `filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `issued` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `municipality` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `period_end` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `period_start` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `region` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_id` bigint(20) DEFAULT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `url_format_id` bigint(20) DEFAULT NULL,
  `access_url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKexb2irkqg90qyai7dwkg1g3yj` (`dataset_id`),
  KEY `FKomy7mq25j3xlxp4jowvmat7d4` (`url_format_id`),
  CONSTRAINT `FKexb2irkqg90qyai7dwkg1g3yj` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`),
  CONSTRAINT `FKomy7mq25j3xlxp4jowvmat7d4` FOREIGN KEY (`url_format_id`) REFERENCES `format` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_event` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  `details` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user` tinyblob,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKofdfglrgk9uep05wog6x0xcw` (`user_id`),
  CONSTRAINT `FKofdfglrgk9uep05wog6x0xcw` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_migrate` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `catalog_id` bigint(20) DEFAULT NULL,
  `category` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `description` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `licence_id` bigint(20) DEFAULT NULL,
  `organization_id` bigint(20) DEFAULT NULL,
  `representative_id` bigint(20) DEFAULT NULL,
  `tags` text COLLATE utf8mb4_lithuanian_ci,
  `theme` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `version` int(11) NOT NULL,
  `update_frequency` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `internal_id` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `origin` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `published` datetime DEFAULT NULL,
  `language` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `temporal_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `spatial_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `is_public` bit(1) DEFAULT NULL,
  `meta` text COLLATE utf8mb4_lithuanian_ci,
  `coordinator_id` bigint(20) DEFAULT NULL,
  `financed` bit(1) DEFAULT NULL,
  `financing_plan_id` bigint(20) DEFAULT NULL,
  `financing_priorities` text COLLATE utf8mb4_lithuanian_ci,
  `financing_received` bigint(20) DEFAULT NULL,
  `financing_required` bigint(20) DEFAULT NULL,
  `priority_score` int(11) DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `soft_deleted` datetime(6) DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `will_be_financed` bit(1) NOT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK95jpd7a0tb2bhuwsv5dy046mm` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_remark` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `author_id` bigint(20) DEFAULT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKb787tufhteyfo5l43abdlj46r` (`author_id`),
  KEY `FKdf213wga71ph9g7uea9bc1cv6` (`dataset_id`),
  CONSTRAINT `FKb787tufhteyfo5l43abdlj46r` FOREIGN KEY (`author_id`) REFERENCES `user` (`id`),
  CONSTRAINT `FKdf213wga71ph9g7uea9bc1cv6` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_resource` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `data` longblob,
  `dataset_id` bigint(20) DEFAULT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `filename` text COLLATE utf8mb4_lithuanian_ci,
  `issued` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `mime` tinytext COLLATE utf8mb4_lithuanian_ci,
  `rating` int(11) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `spatial_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `temporal_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` text COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_resource_migrate` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `data` longblob,
  `dataset_id` bigint(20) DEFAULT NULL,
  `filename` text COLLATE utf8mb4_lithuanian_ci,
  `mime` tinytext COLLATE utf8mb4_lithuanian_ci,
  `rating` int(11) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` text COLLATE utf8mb4_lithuanian_ci,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `temporal` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `spatial` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `spatial_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `temporal_coverage` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `issued` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_structure` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `distribution_version` int(11) DEFAULT NULL,
  `filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_id` bigint(20) DEFAULT NULL,
  `standardized` bit(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK2v2vvx2loa3lbico9oey4stsj` (`dataset_id`),
  CONSTRAINT `FK2v2vvx2loa3lbico9oey4stsj` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_structure_field` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `data_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `db_table_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `order_id` int(11) NOT NULL,
  `scheme` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `standard_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `technical_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK8w1tjayu0ut13h9g7f8f6ryqd` (`dataset_id`),
  CONSTRAINT `FK8w1tjayu0ut13h9g7f8f6ryqd` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `dataset_visit` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `last_visited` datetime DEFAULT NULL,
  `visit_count` int(11) NOT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK5enxj7egeon3u4arv6t8hr8lf` (`dataset_id`),
  CONSTRAINT `FK5enxj7egeon3u4arv6t8hr8lf` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `distribution_format` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `email_template` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `template` text COLLATE utf8mb4_lithuanian_ci,
  `variables` text COLLATE utf8mb4_lithuanian_ci,
  `subject` text COLLATE utf8mb4_lithuanian_ci,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK5bc0ddajl6jdbstkwabi2n092` (`identifier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `external_site` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `faq` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `answer` text COLLATE utf8mb4_lithuanian_ci,
  `question` tinytext COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `file_resource` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `identifier` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `mime_type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `obj_class` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `obj_id` bigint(20) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `type` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `financing_plan` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `financed_datasets` int(11) DEFAULT NULL,
  `financing_plan_state_id` bigint(20) DEFAULT NULL,
  `projected_cost` int(11) DEFAULT NULL,
  `projected_datasets` int(11) DEFAULT NULL,
  `received_financing` int(11) DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `year` int(11) DEFAULT NULL,
  `created_by` bigint(20) DEFAULT NULL,
  `organization_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKek9xiakdr85a16q9yhwbg5sax` (`organization_id`,`year`),
  KEY `FKrue1sug7ymabvpx58i6mcf3ux` (`created_by`),
  CONSTRAINT `FKosf8lm46jp6qbaclte8n7d4s8` FOREIGN KEY (`organization_id`) REFERENCES `organization` (`id`),
  CONSTRAINT `FKrue1sug7ymabvpx58i6mcf3ux` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci COMMENT='Organization dataset financing plan by year';


CREATE TABLE `financing_plan_state` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `details` text COLLATE utf8mb4_lithuanian_ci,
  `financing_plan_id` bigint(20) DEFAULT NULL,
  `status` int(11) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `format` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `extension` tinytext COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `mimetype` text COLLATE utf8mb4_lithuanian_ci,
  `rating` int(11) DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `frequency` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `title_en` tinytext COLLATE utf8mb4_lithuanian_ci,
  `uri` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `geoportal_lt_entry` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `raw_data` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `type` tinytext COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `global_email` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `harvested_visit` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `last_visited` datetime DEFAULT NULL,
  `visit_count` int(11) NOT NULL,
  `harvesting_result_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK4vif4qkrtl19dsxwnii9i0909` (`harvesting_result_id`),
  CONSTRAINT `FK4vif4qkrtl19dsxwnii9i0909` FOREIGN KEY (`harvesting_result_id`) REFERENCES `harvesting_result` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `harvesting_job` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `indexed` bit(1) DEFAULT NULL,
  `schedule` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `started` datetime DEFAULT NULL,
  `stopped` datetime DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `translated` bit(1) DEFAULT NULL,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `organization` bigint(20) DEFAULT NULL,
  `active` bit(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK2ryi0ker86i5vc5f9p48w64wt` (`organization`),
  CONSTRAINT `FK2ryi0ker86i5vc5f9p48w64wt` FOREIGN KEY (`organization`) REFERENCES `organization` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `harvesting_result` (
  `published` bit(1) NOT NULL,
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `remote_id` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  `job_id` bigint(20) DEFAULT NULL,
  `description_en` text COLLATE utf8mb4_lithuanian_ci,
  `keywords` text COLLATE utf8mb4_lithuanian_ci,
  `organization` text COLLATE utf8mb4_lithuanian_ci,
  `raw_data` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `title_en` text COLLATE utf8mb4_lithuanian_ci,
  `category_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK_HARV_RESULT_HARV_JOB` (`job_id`),
  KEY `FK_HARV_RESULT_CATEGORY` (`category_id`),
  CONSTRAINT `FK_HARV_RESULT_CATEGORY` FOREIGN KEY (`category_id`) REFERENCES `category` (`id`),
  CONSTRAINT `FK_HARV_RESULT_HARV_JOB` FOREIGN KEY (`job_id`) REFERENCES `harvesting_job` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `learning_material` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `learning_material_id` bigint(20) DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `topic` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `video_url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `summary` text COLLATE utf8mb4_lithuanian_ci,
  `author_name` tinytext COLLATE utf8mb4_lithuanian_ci,
  `published` date DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `requested` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKqu11paplkqkt2hyre1e2syjgt` (`uuid`),
  KEY `FK67j6xkiixutc3kaxwshn3kd8u` (`user_id`),
  CONSTRAINT `FK67j6xkiixutc3kaxwshn3kd8u` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `licence` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `identifier` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK_1st8clbrf69hv9gl2nhfm0myw` (`identifier`),
  UNIQUE KEY `UK1st8clbrf69hv9gl2nhfm0myw` (`identifier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `municipality` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `national_financing_plan` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `confirmation_date` datetime(6) DEFAULT NULL,
  `confirmed` bit(1) DEFAULT NULL,
  `confirmed_budget` bigint(20) DEFAULT NULL,
  `confirmed_by` bigint(20) DEFAULT NULL,
  `estimated_budget` bigint(20) DEFAULT NULL,
  `year` int(11) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKakpi5bggg3ngiv2l1yocswuwy` (`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `newsletter_subscription` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `is_active` bit(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `news_item` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `author` tinyblob,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `tags` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `summary` text COLLATE utf8mb4_lithuanian_ci,
  `author_name` tinytext COLLATE utf8mb4_lithuanian_ci,
  `is_public` bit(1) DEFAULT NULL,
  `published` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK511y70m0jr63davomeikaxo7v` (`slug`),
  UNIQUE KEY `UK6afehd75fw4450ewl63mpmclk` (`uuid`),
  KEY `FK2bn8yor8clqe8rr80sc4uwqyn` (`user_id`),
  CONSTRAINT `FK2bn8yor8clqe8rr80sc4uwqyn` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `old_password` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `password` char(60) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK3h975gamp3cdbn09ljckuiv3a` (`user_id`),
  CONSTRAINT `FK3h975gamp3cdbn09ljckuiv3a` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `open_data_gov_lt_entry` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `alt_title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `code` tinytext COLLATE utf8mb4_lithuanian_ci,
  `contact_info` text COLLATE utf8mb4_lithuanian_ci,
  `data_extent` text COLLATE utf8mb4_lithuanian_ci,
  `data_trustworthiness` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_begins` tinytext COLLATE utf8mb4_lithuanian_ci,
  `dataset_conditions` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_ends` tinytext COLLATE utf8mb4_lithuanian_ci,
  `dataset_type` tinytext COLLATE utf8mb4_lithuanian_ci,
  `date_meta_published` tinytext COLLATE utf8mb4_lithuanian_ci,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `format` tinytext COLLATE utf8mb4_lithuanian_ci,
  `keywords` text COLLATE utf8mb4_lithuanian_ci,
  `publisher` text COLLATE utf8mb4_lithuanian_ci,
  `refresh_period` tinytext COLLATE utf8mb4_lithuanian_ci,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `topic` text COLLATE utf8mb4_lithuanian_ci,
  `url` text COLLATE utf8mb4_lithuanian_ci,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `organization` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `municipality` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `region` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `address` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `company_code` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `is_public` bit(1) DEFAULT NULL,
  `phone` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `jurisdiction` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `website` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKh2su5s2veeq84vjfeb4s87tep` (`slug`),
  UNIQUE KEY `UKs9xj0yg0stek0h7hedcn2qro3` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `partner_application` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `email` text COLLATE utf8mb4_lithuanian_ci,
  `filename` text COLLATE utf8mb4_lithuanian_ci,
  `letter` longblob,
  `organization_title` text COLLATE utf8mb4_lithuanian_ci,
  `phone` text COLLATE utf8mb4_lithuanian_ci,
  `viisp_email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `viisp_first_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `viisp_last_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `viisp_phone` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `viisp_dob` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `password_reset_token` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `expiry_date` datetime(6) DEFAULT NULL,
  `token` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) NOT NULL,
  `used_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FK5lwtbncug84d4ero33v3cfxvl` (`user_id`),
  CONSTRAINT `FK5lwtbncug84d4ero33v3cfxvl` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `published_report` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `data` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `title` text COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `region` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `title` tinytext COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `report` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `body` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `representative` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `first_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `last_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `organization_id` bigint(20) DEFAULT NULL,
  `phone` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `request` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `dataset_id` bigint(20) DEFAULT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `format` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `is_existing` bit(1) NOT NULL,
  `notes` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `organization_id` bigint(20) DEFAULT NULL,
  `periodicity` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `planned_opening_date` date DEFAULT NULL,
  `purpose` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `changes` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `is_public` bit(1) NOT NULL,
  `structure_data` mediumtext COLLATE utf8mb4_lithuanian_ci,
  `structure_filename` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK6dgywmcxa5qo4onrx95vxe5hf` (`slug`),
  UNIQUE KEY `UKopq611dvscynyvfpgpbvig29v` (`uuid`),
  KEY `FKqws2fdeknk90txm7qnm9bxd07` (`user_id`),
  CONSTRAINT `FKqws2fdeknk90txm7qnm9bxd07` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `request_event` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `meta` text COLLATE utf8mb4_lithuanian_ci,
  `type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `request_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKboyhtgld73e9xslhlemxax5n` (`request_id`),
  CONSTRAINT `FKboyhtgld73e9xslhlemxax5n` FOREIGN KEY (`request_id`) REFERENCES `request` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `request_structure` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `data_notes` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `data_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `data_type` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `dictionary_title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `request_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `sent_mail` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `recipient` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `sso_token` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `ip` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `token` varchar(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UKbf4iv8dfxpwfmh5e2xupfqqsa` (`token`),
  KEY `FKkju7shggmw61xqmyw2ha2u6hn` (`user_id`),
  CONSTRAINT `FKkju7shggmw61xqmyw2ha2u6hn` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `suggestion` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `email` tinytext COLLATE utf8mb4_lithuanian_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `terms_of_use` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `file` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `body` text COLLATE utf8mb4_lithuanian_ci,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `published` date DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `usecase` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `beneficiary_group` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `benefit` text COLLATE utf8mb4_lithuanian_ci,
  `description` text COLLATE utf8mb4_lithuanian_ci,
  `extra_information` text COLLATE utf8mb4_lithuanian_ci,
  `slug` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `status` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `url` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `uuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `comment` text COLLATE utf8mb4_lithuanian_ci,
  `imageuuid` char(36) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK1oeiv5hog092d0ogeb8ra7nig` (`slug`),
  UNIQUE KEY `UKfqd3n77pj91v0j47gl6adkyo1` (`uuid`),
  KEY `FKu1uqn07hiom0uhv2fg22d6ou` (`user_id`),
  CONSTRAINT `FKu1uqn07hiom0uhv2fg22d6ou` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `usecase_dataset_ids` (
  `usecase_id` bigint(20) NOT NULL,
  `dataset_ids` bigint(20) DEFAULT NULL,
  KEY `FKjojfec74pegtfn2xre9ycrkgn` (`usecase_id`),
  CONSTRAINT `FKjojfec74pegtfn2xre9ycrkgn` FOREIGN KEY (`usecase_id`) REFERENCES `usecase` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `usecase_like` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime DEFAULT NULL,
  `modified` datetime DEFAULT NULL,
  `version` int(11) NOT NULL,
  `usecase_uuid` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `first_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `last_name` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `password` char(60) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `role` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `organization_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `phone` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `needs_password_change` bit(1) NOT NULL,
  `year_of_birth` int(11) DEFAULT NULL,
  `disabled` bit(1) NOT NULL,
  `suspended` bit(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `UK_ob8kqyqqgmefl0aco34akdtpe` (`email`),
  UNIQUE KEY `UKob8kqyqqgmefl0aco34akdtpe` (`email`),
  KEY `FKi3ynrf4qjomj2hdjx7ssa3mlh` (`organization_id`),
  CONSTRAINT `FKi3ynrf4qjomj2hdjx7ssa3mlh` FOREIGN KEY (`organization_id`) REFERENCES `organization` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci COMMENT='ADP user of any kind';


CREATE TABLE `user_dataset_subscription` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `dataset` bigint(20) DEFAULT NULL,
  `user` bigint(20) DEFAULT NULL,
  `active` bit(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `FKfuokd2v3s9sdobtggqtiuxjog` (`dataset`),
  KEY `FKpbl2oik54h31p0fyq4n72wetv` (`user`),
  CONSTRAINT `FKfuokd2v3s9sdobtggqtiuxjog` FOREIGN KEY (`dataset`) REFERENCES `dataset` (`id`),
  CONSTRAINT `FKpbl2oik54h31p0fyq4n72wetv` FOREIGN KEY (`user`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `user_like` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `request_id` bigint(20) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `user_table_preferences` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `table_column_string` text COLLATE utf8mb4_lithuanian_ci,
  `table_id` varchar(255) COLLATE utf8mb4_lithuanian_ci DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


CREATE TABLE `user_vote` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created` datetime(6) DEFAULT NULL,
  `deleted` bit(1) DEFAULT NULL,
  `deleted_on` datetime(6) DEFAULT NULL,
  `modified` datetime(6) DEFAULT NULL,
  `version` int(11) NOT NULL,
  `rating` int(11) NOT NULL,
  `dataset_id` bigint(20) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `harvested_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `FKq0c0k0uxbtdrldpfdtlq1jai7` (`dataset_id`),
  KEY `FK2q50phs57njg6g0qvha1r8703` (`user_id`),
  KEY `FKmaho12gli2m957igj2bxsu7o0` (`harvested_id`),
  CONSTRAINT `FK2q50phs57njg6g0qvha1r8703` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `FKmaho12gli2m957igj2bxsu7o0` FOREIGN KEY (`harvested_id`) REFERENCES `harvesting_result` (`id`),
  CONSTRAINT `FKq0c0k0uxbtdrldpfdtlq1jai7` FOREIGN KEY (`dataset_id`) REFERENCES `dataset` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_lithuanian_ci;


-- 2022-07-27 10:15:48

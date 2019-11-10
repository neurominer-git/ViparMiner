-- MySQL dump 10.13  Distrib 5.5.37, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: vipar
-- ------------------------------------------------------
-- Server version	5.5.37-0ubuntu0.12.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `datadictionaries`
--

DROP TABLE IF EXISTS `datadictionaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `datadictionaries` (
  `dd_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `dd_version` mediumint(4) unsigned NOT NULL,
  `dd_date` varchar(50) NOT NULL,
  `study` int(11) unsigned NOT NULL,
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`dd_auto`),
  KEY `study` (`study`),
  CONSTRAINT `datadictionaries_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `datadictionaries_variables`
--

DROP TABLE IF EXISTS `datadictionaries_variables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `datadictionaries_variables` (
  `dv_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `dd_version` int(11) unsigned NOT NULL,
  `variable` int(11) unsigned NOT NULL,
  PRIMARY KEY (`dv_auto`),
  KEY `variable` (`variable`),
  KEY `dd_version` (`dd_version`),
  CONSTRAINT `datadictionaries_variables_ibfk_1` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE,
  CONSTRAINT `datadictionaries_variables_ibfk_2` FOREIGN KEY (`dd_version`) REFERENCES `datadictionaries` (`dd_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `messageboard`
--

DROP TABLE IF EXISTS `messageboard`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `messageboard` (
  `mb_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `user` int(11) unsigned NOT NULL,
  `project` int(11) unsigned NOT NULL,
  `message` varchar(255) DEFAULT NULL,
  `date` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`mb_auto`),
  KEY `user` (`user`),
  KEY `project` (`project`),
  CONSTRAINT `messageboard_ibfk_1` FOREIGN KEY (`user`) REFERENCES `users` (`u_auto`) ON DELETE CASCADE,
  CONSTRAINT `messageboard_ibfk_2` FOREIGN KEY (`project`) REFERENCES `projects` (`p_auto`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `missing`
--

DROP TABLE IF EXISTS `missing`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `missing` (
  `m_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `value` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `study` int(11) unsigned NOT NULL,
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`m_auto`),
  KEY `study` (`study`),
  CONSTRAINT `missing_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projects`
--

DROP TABLE IF EXISTS `projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `projects` (
  `p_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `project` varchar(50) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `display` tinyint(1) NOT NULL DEFAULT '0',
  `res` tinyint(1) NOT NULL DEFAULT '0',
  `study` int(11) unsigned NOT NULL,
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`p_auto`),
  KEY `study` (`study`),
  CONSTRAINT `projects_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `projects_variables`
--

DROP TABLE IF EXISTS `projects_variables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `projects_variables` (
  `project` int(11) unsigned NOT NULL,
  `variable` int(11) unsigned NOT NULL,
  KEY `project` (`project`),
  KEY `variable` (`variable`),
  CONSTRAINT `projects_variables_ibfk_1` FOREIGN KEY (`project`) REFERENCES `projects` (`p_auto`) ON DELETE CASCADE,
  CONSTRAINT `projects_variables_ibfk_2` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `resources`
--

DROP TABLE IF EXISTS `resources`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `resources` (
  `r_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `resource` varchar(50) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `datadictionary` int(11) unsigned NOT NULL,
  `server` int(11) unsigned NOT NULL,
  `cert_user` int(11) unsigned NOT NULL,
  `cert_date` datetime DEFAULT NULL,
  `cert` tinyint(1) NOT NULL DEFAULT '-1',
  `rcount` int(20) DEFAULT '0',
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  `study` int(11) unsigned NOT NULL,
  PRIMARY KEY (`r_auto`),
  KEY `server` (`server`),
  KEY `study` (`study`),
  KEY `datadictionary` (`datadictionary`),
  CONSTRAINT `resources_ibfk_1` FOREIGN KEY (`server`) REFERENCES `server` (`sv_auto`) ON DELETE CASCADE,
  CONSTRAINT `resources_ibfk_2` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE,
  CONSTRAINT `resources_ibfk_3` FOREIGN KEY (`datadictionary`) REFERENCES `datadictionaries` (`dd_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `run_date`
--

DROP TABLE IF EXISTS `run_date`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `run_date` (
  `rd_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `run_date` varchar(11) DEFAULT NULL,
  PRIMARY KEY (`rd_auto`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `run_stats`
--

DROP TABLE IF EXISTS `run_stats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `run_stats` (
  `run_time` int(11) unsigned NOT NULL,
  `resource` int(11) unsigned NOT NULL,
  `time` float(7,2) DEFAULT NULL,
  `records` int(10) DEFAULT NULL,
  KEY `resource` (`resource`),
  KEY `run_time` (`run_time`),
  CONSTRAINT `run_stats_ibfk_1` FOREIGN KEY (`resource`) REFERENCES `resources` (`r_auto`) ON DELETE CASCADE,
  CONSTRAINT `run_stats_ibfk_2` FOREIGN KEY (`run_time`) REFERENCES `run_time` (`rt_auto`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `run_syntax`
--

DROP TABLE IF EXISTS `run_syntax`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `run_syntax` (
  `run_time` int(11) unsigned NOT NULL,
  `syntax` mediumblob,
  KEY `run_time` (`run_time`),
  CONSTRAINT `run_syntax_ibfk_1` FOREIGN KEY (`run_time`) REFERENCES `run_time` (`rt_auto`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `run_time`
--

DROP TABLE IF EXISTS `run_time`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `run_time` (
  `rt_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `project` int(11) unsigned NOT NULL,
  `run_date` int(11) unsigned NOT NULL,
  `user` int(11) unsigned NOT NULL,
  `run_time` varchar(255) DEFAULT NULL,
  `exclude` int(1) DEFAULT '0',
  `shared` int(1) DEFAULT '0',
  `run_status` int(1) DEFAULT '0',
  `description` varchar(255) DEFAULT '',
  PRIMARY KEY (`rt_auto`),
  KEY `run_date` (`run_date`),
  KEY `project` (`project`),
  KEY `user` (`user`),
  CONSTRAINT `run_time_ibfk_1` FOREIGN KEY (`run_date`) REFERENCES `run_date` (`rd_auto`) ON DELETE CASCADE,
  CONSTRAINT `run_time_ibfk_2` FOREIGN KEY (`project`) REFERENCES `projects` (`p_auto`) ON DELETE CASCADE,
  CONSTRAINT `run_time_ibfk_3` FOREIGN KEY (`user`) REFERENCES `users` (`u_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `server`
--

DROP TABLE IF EXISTS `server`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `server` (
  `sv_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `site` int(11) unsigned NOT NULL,
  `port` mediumint(8) unsigned DEFAULT NULL,
  `remotehost` varchar(100) DEFAULT NULL,
  `remoteport` int(5) NOT NULL DEFAULT '22',
  `remoteuser` varchar(20) NOT NULL DEFAULT 'vipar',
  `available` tinyint(1) DEFAULT '-1',
  `Lastcheck` varchar(30) DEFAULT '',
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`sv_auto`),
  KEY `site` (`site`),
  CONSTRAINT `server_ibfk_1` FOREIGN KEY (`site`) REFERENCES `site` (`s_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `site`
--

DROP TABLE IF EXISTS `site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `site` (
  `s_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `shortname` varchar(50) NOT NULL,
  `country` varchar(50) DEFAULT NULL,
  `fullname` varchar(255) DEFAULT NULL,
  `study` int(11) unsigned NOT NULL,
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`s_auto`),
  KEY `study` (`study`),
  CONSTRAINT `site_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `study`
--

DROP TABLE IF EXISTS `study`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `study` (
  `st_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `study` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`st_auto`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `studyprivs`
--

DROP TABLE IF EXISTS `studyprivs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `studyprivs` (
  `sp_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`sp_auto`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `u_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) DEFAULT NULL,
  `password` varchar(50) DEFAULT NULL,
  `time_zone` varchar(50) DEFAULT NULL,
  `email` varchar(50) DEFAULT NULL,
  `it` tinyint(1) unsigned DEFAULT '0',
  `delstat` tinyint(1) unsigned DEFAULT '0',
  PRIMARY KEY (`u_auto`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users_projects`
--

DROP TABLE IF EXISTS `users_projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users_projects` (
  `up_auto` int(11) NOT NULL AUTO_INCREMENT,
  `user` int(11) unsigned NOT NULL,
  `project` int(11) unsigned NOT NULL,
  `user_level` int(1) DEFAULT '1',
  PRIMARY KEY (`up_auto`),
  KEY `project` (`project`),
  KEY `user` (`user`),
  CONSTRAINT `users_projects_ibfk_1` FOREIGN KEY (`project`) REFERENCES `projects` (`p_auto`) ON DELETE CASCADE,
  CONSTRAINT `users_projects_ibfk_2` FOREIGN KEY (`user`) REFERENCES `users` (`u_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users_study`
--

DROP TABLE IF EXISTS `users_study`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users_study` (
  `us_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `user` int(11) unsigned DEFAULT NULL,
  `study` int(11) unsigned DEFAULT NULL,
  `priv` int(11) unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`us_auto`),
  KEY `study` (`study`),
  KEY `user` (`user`),
  KEY `priv` (`priv`),
  CONSTRAINT `users_study_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE,
  CONSTRAINT `users_study_ibfk_2` FOREIGN KEY (`user`) REFERENCES `users` (`u_auto`) ON DELETE CASCADE,
  CONSTRAINT `users_study_ibfk_3` FOREIGN KEY (`priv`) REFERENCES `studyprivs` (`sp_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables`
--

DROP TABLE IF EXISTS `variables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables` (
  `v_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `variable` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `study` int(11) unsigned NOT NULL,
  `type` int(11) unsigned NOT NULL DEFAULT '0',
  `delstat` tinyint(1) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`v_auto`),
  KEY `study` (`study`),
  KEY `type` (`type`),
  CONSTRAINT `variables_ibfk_1` FOREIGN KEY (`study`) REFERENCES `study` (`st_auto`) ON DELETE CASCADE,
  CONSTRAINT `variables_ibfk_2` FOREIGN KEY (`type`) REFERENCES `variables_type` (`vt_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables_cat`
--

DROP TABLE IF EXISTS `variables_cat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables_cat` (
  `vcat_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `variable` int(11) unsigned NOT NULL,
  `cat` int(11) unsigned NOT NULL,
  `code` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`vcat_auto`),
  KEY `v_idx` (`variable`),
  CONSTRAINT `variables_cat_ibfk_1` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables_con`
--

DROP TABLE IF EXISTS `variables_con`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables_con` (
  `vcon_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `variable` int(11) unsigned NOT NULL,
  `min` float DEFAULT NULL,
  `max` float DEFAULT NULL,
  `prec` smallint(2) NOT NULL DEFAULT '1',
  PRIMARY KEY (`vcon_auto`),
  KEY `v_idx` (`variable`),
  CONSTRAINT `variables_con_ibfk_1` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables_dat`
--

DROP TABLE IF EXISTS `variables_dat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables_dat` (
  `vdat_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `variable` int(11) unsigned NOT NULL,
  `min` date DEFAULT NULL,
  `max` date DEFAULT NULL,
  PRIMARY KEY (`vdat_auto`),
  KEY `v_idx` (`variable`),
  CONSTRAINT `variables_dat_ibfk_1` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables_missing`
--

DROP TABLE IF EXISTS `variables_missing`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables_missing` (
  `vm_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `variable` int(11) unsigned NOT NULL,
  `missing` int(11) unsigned NOT NULL,
  PRIMARY KEY (`vm_auto`),
  KEY `variable` (`variable`),
  KEY `missing` (`missing`),
  CONSTRAINT `variables_missing_ibfk_1` FOREIGN KEY (`variable`) REFERENCES `variables` (`v_auto`) ON DELETE CASCADE,
  CONSTRAINT `variables_missing_ibfk_2` FOREIGN KEY (`missing`) REFERENCES `missing` (`m_auto`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `variables_type`
--

DROP TABLE IF EXISTS `variables_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `variables_type` (
  `vt_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `type` varchar(20) NOT NULL,
  PRIMARY KEY (`vt_auto`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vipar_config`
--

DROP TABLE IF EXISTS `vipar_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vipar_config` (
  `v_auto` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `v_section` varchar(20) NOT NULL,
  `v_key` varchar(20) NOT NULL,
  `v_value` varchar(100) NOT NULL,
  PRIMARY KEY (`v_auto`)
) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2014-06-10 19:38:31

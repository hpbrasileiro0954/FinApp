BEGIN TRANSACTION;

PRAGMA foreign_keys = ON;

-- --------------------------------------------------------

--
-- Table structure for table `categories`
--

DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`name` VARCHAR(512) DEFAULT '',
	`published` INTEGER DEFAULT 0,
	`vl_prev` REAL DEFAULT 0.0000,
	`day_prev` INTEGER DEFAULT 0,
	`ordem` INTEGER DEFAULT 0,
	`type` VARCHAR(25) DEFAULT '',
	`created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------

--
-- Table structure for table `entries`
--

DROP TABLE IF EXISTS `entries`;
CREATE TABLE `entries` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`category_id` INTEGER DEFAULT 0,
	`dt_entry` DATETIME DEFAULT '0000-00-00 00:00:00',
	`vl_entry` REAL DEFAULT 0.0000,
	`nm_entry` VARCHAR(50) DEFAULT '',
	`ds_category` VARCHAR(255) DEFAULT '',
	`ds_subcategory` VARCHAR(255) DEFAULT '',
	`status` INTEGER DEFAULT 0,
	`fixed_costs` INTEGER DEFAULT 0,
	`checked` INTEGER DEFAULT 0,
	`published` INTEGER DEFAULT 0,
	`ds_detail` VARCHAR(255) DEFAULT '',
	`created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`mysql_id` INTEGER DEFAULT 0,
	CONSTRAINT FK_Entry_Category FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- --------------------------------------------------------

--
-- Table structure for table `facts`
--

DROP TABLE IF EXISTS `facts`;
CREATE TABLE `facts` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`entry_id` INTEGER DEFAULT 0,
	`category_id` INTEGER DEFAULT 0,
	`dt_fact` DATETIME DEFAULT '0000-00-00 00:00:00',
	`vl_fact` REAL DEFAULT 0.0000,
	`nm_fact` VARCHAR(50) DEFAULT '',
	`ds_category` VARCHAR(255) DEFAULT '',
	`ds_subcategory` VARCHAR(255) DEFAULT '',
	`status` INTEGER DEFAULT 0,
	`fixed_costs` INTEGER DEFAULT 0,
	`checked` INTEGER DEFAULT 0,
	`published` INTEGER DEFAULT 0,
	`ds_detail` VARCHAR(255) DEFAULT '',
	`created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`mysql_id` INTEGER DEFAULT 0,
	CONSTRAINT FK_Fact_Entry FOREIGN KEY (`entry_id`) REFERENCES `entries`(`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT FK_Fact_Category FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- --------------------------------------------------------

--
-- Table structure for table `params`
--

DROP TABLE IF EXISTS `params`;
CREATE TABLE `params` (
	`id` INTEGER PRIMARY KEY AUTOINCREMENT,
	`label` VARCHAR(50) DEFAULT '',
	`value` VARCHAR(50) DEFAULT '',
	`default` VARCHAR(50) DEFAULT '',
	`dt_params` DATETIME DEFAULT '',
	`created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
	`type` VARCHAR(100) DEFAULT '',
	`mysql_id` INTEGER DEFAULT 0
);

COMMIT;

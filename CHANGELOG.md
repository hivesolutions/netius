# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

*

### Changed

*

### Fixed

*

## [1.19.8] - 2024-04-23

### Changed

* Moved flush operation up in the chain

## [1.19.7] - 2024-04-23

### Changed

* Flush of loggers before on logger unloading

## [1.19.6] - 2024-04-23

### Changed

* Optional `raise_e` support in `LogstashHandler`

## [1.19.5] - 2024-04-23

### Fixed

* Support for multiple messages for same SMTP session - [#40](https://github.com/hivesolutions/netius/issues/40)

## [1.19.4] - 2024-04-22

### Added

* Support for `.env` file loading
* LogstashHandler support using `LOGGING_LOGSTASH` and `LOGSTASH_BASE_URL`

## [1.19.3] - 2024-01-18

### Changed

* Improved the structure of the Postmaster message

### Fixed

* Context information `tos` in the Postmaster email handling
* Critical issue with the SMTP client when connecting with SMTP servers with older versions of OpenSSL

## [1.19.2] - 2024-01-17

### Added

* Support for Postmaster email in SMTP relay using the `POSTMASTER` configuration value
* Support for the `exception` event in the `Connection` triggered when a exception is raised in the connection domain

## [1.19.1] - 2022-10-15

### Added

* Support for `allowed_froms` in SMTP relay

### Changed

* Improved support in the `legacy.py` module

## [1.19.0] - 2022-05-02

### Added

* Support for `SSL_CONTEXT_OPTIONS` to netius SSL context creation

## [1.18.4] - 2022-04-26

### Added

* Better debug support for connection address

### Fixed

* Custom listing using both `apache` and `legacy` for `LIST_ENGINE`

## [1.18.3] - 2021-11-01

### Added

* Better debug support for connection address

## [1.18.2] - 2021-05-01

### Added

* Support for `redirect_regex` in `proxy_r`

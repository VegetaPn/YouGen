# Changelog

## [Unreleased]

### Added
- ✨ **Browser automation for comment posting** - Use agent-browser to avoid Twitter bot detection
- ✨ **Language matching** - Comments automatically match tweet language (EN/CN/JP)
- ✨ **Auto-reload influencers** - Automatically reload `influencers.yaml` when modified
- ✅ **Complete test suite** - 58 unit tests with 100% pass rate

### Changed
- 🔄 **Default to browser mode** - Comments are now posted via agent-browser by default
- 📝 **Enhanced system prompts** - Added explicit language matching instructions
- 🔧 **Improved configuration** - Better file modification detection

### Fixed
- 🐛 **Bird CLI rate limiting** - Replaced with browser automation to avoid API limits
- 🐛 **Influencer reload** - Config changes now properly detected and reloaded

### Technical
- Added `BrowserClient` class for agent-browser integration
- Modified `Reviewer` and CLI to support both bird and browser modes
- Updated all imports to use absolute paths (Python 3.10+ compatible)
- All external calls properly mocked in tests

## [0.1.0] - 2026-01-21

### Initial Release
- 🚀 Twitter growth automation MVP
- 📊 Trend analysis and scoring
- 💬 Claude-powered comment generation
- ✅ Interactive CLI review workflow
- 📁 JSON file storage (no database needed)
- 🔒 Comprehensive test coverage

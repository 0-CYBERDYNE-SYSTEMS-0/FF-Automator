#!/usr/bin/env python3
"""
Debug BBC News Access and Max Steps Issues

This script addresses the issues found in your logs:
1. Tasks failing at max steps (20-30 seconds)
2. Inability to access BBC News or click "Top Stories" link
3. Configuration problems with web automation
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mlx_use.controller.service import Controller
from mlx_use.agent.service import Agent
from mlx_use.agent.llm_models import get_llm
from mlx_use.mac.tree import MacUITreeBuilder
from mlx_use.telemetry.service import ProductTelemetry


class BBCNewsDebugger:
    """Debug BBC News automation issues"""

    def __init__(self):
        self.results = {}
        self.issues_found = []

    def log_issue(self, issue: str, severity: str = "warning"):
        """Log a found issue"""
        issue_data = {
            "issue": issue,
            "severity": severity,
            "timestamp": time.time()
        }
        self.issues_found.append(issue_data)
        print(f"{'❌' if severity == 'error' else '⚠️'} {issue}")

    def log_success(self, message: str):
        """Log a successful test"""
        print(f"✅ {message}")

    async def test_1_basic_agent_config(self):
        """Test 1: Basic Agent Configuration and Max Steps"""
        print("\n🔧 Test 1: Basic Agent Configuration")
        print("-" * 50)

        try:
            # Test with different max steps configurations
            test_configs = [
                {"max_steps": 10, "max_actions_per_step": 3},
                {"max_steps": 25, "max_actions_per_step": 5},
                {"max_steps": 50, "max_actions_per_step": 10},
                {"max_steps": 100, "max_actions_per_step": 10}
            ]

            for config in test_configs:
                print(f"\n  Testing config: {config}")

                # Create a simple task that should succeed quickly
                llm = get_llm("OpenAI", "gpt-4o-mini")  # Use reliable model
                controller = Controller()
                mac_tree_builder = MacUITreeBuilder()

                agent = Agent(
                    task="Open Calculator app",
                    llm=llm,
                    controller=controller,
                    max_actions_per_step=config["max_actions_per_step"],
                    max_failures=3,
                    use_vision=False
                )

                # Time the execution
                start_time = time.time()
                try:
                    # Set timeout to prevent hanging
                    result = await asyncio.wait_for(
                        agent.run(max_steps=config["max_steps"]),
                        timeout=60  # 60 second timeout
                    )
                    duration = time.time() - start_time

                    success = "Calculator" in str(result).lower()
                    print(f"    Time: {duration:.1f}s, Success: {success}")

                    if duration > 30:
                        self.log_issue(f"Config {config} took too long: {duration:.1f}s")

                except asyncio.TimeoutError:
                    self.log_issue(f"Config {config} timed out after 60s", "error")
                except Exception as e:
                    self.log_issue(f"Config {config} failed: {str(e)}", "error")

        except Exception as e:
            self.log_issue(f"Agent config test failed: {str(e)}", "error")

    async def test_2_browser_actions(self):
        """Test 2: Browser Action Availability"""
        print("\n🌐 Test 2: Browser Action Availability")
        print("-" * 50)

        try:
            # Check what actions are available
            controller = Controller()

            # Get registered actions
            if hasattr(controller, 'registry') and hasattr(controller.registry, 'actions'):
                actions = list(controller.registry.actions.keys())
                print(f"    Available actions: {len(actions)}")

                # Look for browser/web related actions
                web_actions = [action for action in actions if any(keyword in action.lower() for keyword in ['browser', 'web', 'url', 'page', 'safari', 'chrome'])]
                print(f"    Web-related actions: {web_actions}")

                if not web_actions:
                    self.log_issue("No browser automation actions found", "error")

                # Look for navigation actions
                nav_actions = [action for action in actions if any(keyword in action.lower() for keyword in ['open', 'launch', 'start'])]
                print(f"    Navigation actions: {nav_actions[:10]}...")  # Show first 10

            else:
                self.log_issue("Cannot access action registry", "error")

        except Exception as e:
            self.log_issue(f"Browser actions test failed: {str(e)}", "error")

    async def test_3_web_access_direct(self):
        """Test 3: Direct Web Access with Playwright"""
        print("\n🌍 Test 3: Direct Web Access")
        print("-" * 50)

        try:
            # Test Playwright directly
            from playwright.async_api import async_playwright

            async def test_bbc_access():
                async with async_playwright() as p:
                    # Launch browser
                    browser = await p.chromium.launch(headless=False)
                    page = await browser.new_page()

                    # Navigate to BBC News
                    print("    Navigating to BBC News...")
                    await page.goto("https://www.bbc.com/news", timeout=30000)

                    # Get page title
                    title = await page.title()
                    print(f"    Page title: {title}")

                    # Look for Top Stories links
                    print("    Searching for Top Stories links...")
                    links = await page.evaluate('''
                        () => {
                            const links = Array.from(document.querySelectorAll('a'));
                            return links
                                .filter(link => {
                                    const text = link.textContent || '';
                                    const href = link.href || '';
                                    return text.toLowerCase().includes('top stories') ||
                                           text.toLowerCase().includes('top story') ||
                                           href.toLowerCase().includes('top-stories') ||
                                           text.toLowerCase().includes('news');
                                })
                                .map(link => ({
                                    text: link.textContent.trim(),
                                    href: link.href
                                }));
                        }
                    ''')

                    print(f"    Found {len(links)} potentially relevant links:")
                    for i, link in enumerate(links[:5]):  # Show first 5
                        print(f"      {i+1}. '{link['text']}' -> {link['href']}")

                    # Take screenshot for debugging
                    await page.screenshot(path=f"/tmp/bbc_news_{int(time.time())}.png")
                    print("    Screenshot saved for debugging")

                    await browser.close()
                    return {"title": title, "links": links}

            # Run the test with timeout
            result = await asyncio.wait_for(test_bbc_access(), timeout=90)
            self.log_success(f"Successfully accessed BBC News: {result['title']}")

            if not result['links']:
                self.log_issue("No 'Top Stories' links found on BBC News homepage")
            else:
                # Check if we found actual Top Stories links
                top_stories_links = [link for link in result['links'] if 'top stories' in link['text'].lower()]
                if not top_stories_links:
                    self.log_issue("BBC News may have changed - no 'Top Stories' links found")

        except asyncio.TimeoutError:
            self.log_issue("Web access test timed out after 90s", "error")
        except Exception as e:
            self.log_issue(f"Web access test failed: {str(e)}", "error")

    async def test_4_agent_with_playwright(self):
        """Test 4: Agent with Playwright Integration"""
        print("\n🤖 Test 4: Agent with Enhanced Browser Automation")
        print("-" * 50)

        try:
            # Create custom browser action
            from playwright.async_api import async_playwright

            async def open_bbc_news_with_playwright():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=False)
                    page = await browser.new_page()
                    await page.goto("https://www.bbc.com/news")
                    await page.wait_for_load_state("networkidle")
                    return {"browser": browser, "page": page}

            # Simple test task
            task = "Use Playwright to open BBC News and get the page title"
            print(f"    Testing task: {task}")

            # This would need custom agent integration
            # For now, just verify the concept works
            result = await open_bbc_news_with_playwright()
            self.log_success(f"Playwright integration working: {result['page'].url}")

            await result['browser'].close()

        except Exception as e:
            self.log_issue(f"Agent Playwright test failed: {str(e)}", "error")

    async def test_5_timeout_investigation(self):
        """Test 5: Investigate Timeout Issues"""
        print("\n⏱️ Test 5: Timeout Investigation")
        print("-" * 50)

        # Test different timeout scenarios
        timeout_tests = [
            {"timeout": 10, "description": "Very short timeout"},
            {"timeout": 30, "description": "Short timeout"},
            {"timeout": 60, "description": "Medium timeout"},
            {"timeout": 120, "description": "Long timeout"}
        ]

        for test in timeout_tests:
            print(f"\n  Testing {test['description']} ({test['timeout']}s)")

            try:
                llm = get_llm("OpenAI", "gpt-4o-mini")
                controller = Controller()

                agent = Agent(
                    task="Open System Preferences",
                    llm=llm,
                    controller=controller,
                    max_actions_per_step=3,
                    max_failures=2,
                    use_vision=False
                )

                start_time = time.time()
                try:
                    result = await asyncio.wait_for(
                        agent.run(max_steps=5),
                        timeout=test['timeout']
                    )
                    duration = time.time() - start_time

                    if duration > test['timeout'] * 0.8:  # If it took more than 80% of timeout
                        self.log_issue(f"Test took {duration:.1f}s with {test['timeout']}s timeout - close to limit")

                except asyncio.TimeoutError:
                    duration = time.time() - start_time
                    self.log_issue(f"Test timed out after {duration:.1f}s (limit: {test['timeout']}s)", "error")

            except Exception as e:
                self.log_issue(f"Timeout test {test['description']} failed: {str(e)}")

    async def test_6_bbc_news_structure_analysis(self):
        """Test 6: Analyze BBC News Structure"""
        print("\n📰 Test 6: BBC News Structure Analysis")
        print("-" * 50)

        try:
            from playwright.async_api import async_playwright

            async def analyze_bbc_structure():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=False)
                    page = await browser.new_page()
                    await page.goto("https://www.bbc.com/news")
                    await page.wait_for_load_state("networkidle")

                    # Analyze page structure
                    structure = await page.evaluate('''
                        () => {
                            const result = {
                                mainNavigation: [],
                                sections: [],
                                links: []
                            };

                            // Main navigation
                            const nav = document.querySelector('nav') || document.querySelector('[role="navigation"]');
                            if (nav) {
                                const navLinks = nav.querySelectorAll('a');
                                result.mainNavigation = Array.from(navLinks).map(link => ({
                                    text: link.textContent.trim(),
                                    href: link.href
                                }));
                            }

                            // Sections and headings
                            const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                            result.sections = Array.from(headings).map(heading => ({
                                level: heading.tagName,
                                text: heading.textContent.trim()
                            }));

                            // All links with context
                            const allLinks = document.querySelectorAll('a[href]');
                            result.links = Array.from(allLinks).slice(0, 20).map(link => {
                                const parent = link.closest('section, div, article');
                                const context = parent ? parent.className : '';
                                return {
                                    text: link.textContent.trim(),
                                    href: link.href,
                                    context: context
                                };
                            });

                            return result;
                        }
                    ''')

                    await browser.close()
                    return structure

            structure = await asyncio.wait_for(analyze_bbc_structure(), timeout=60)
            self.log_success("Successfully analyzed BBC News structure")

            print(f"    Main navigation items: {len(structure['mainNavigation'])}")
            for item in structure['mainNavigation'][:5]:
                print(f"      - {item['text']}")

            print(f"    Sections found: {len(structure['sections'])}")
            for section in structure['sections'][:5]:
                print(f"      - {section['level']}: {section['text']}")

            # Look for news/story related content
            news_links = [link for link in structure['links'] if any(keyword in link['text'].lower() for keyword in ['story', 'news', 'top', 'headline'])]
            print(f"    News-related links: {len(news_links)}")
            for link in news_links[:5]:
                print(f"      - '{link['text']}' ({link['context']})")

            if not news_links:
                self.log_issue("No clear news/story navigation links found")

        except Exception as e:
            self.log_issue(f"BBC structure analysis failed: {str(e)}", "error")

    async def run_all_tests(self):
        """Run all debugging tests"""
        print("🚀 Starting BBC News Access Debug Session")
        print("=" * 60)
        print("Investigating:")
        print("- Max steps timeout issues")
        print("- BBC News access problems")
        print("- 'Top Stories' link detection")
        print("- Browser automation capabilities")
        print("=" * 60)

        start_time = time.time()

        try:
            await self.test_1_basic_agent_config()
            await self.test_2_browser_actions()
            await self.test_3_web_access_direct()
            await self.test_4_agent_with_playwright()
            await self.test_5_timeout_investigation()
            await self.test_6_bbc_news_structure_analysis()

        except Exception as e:
            self.log_issue(f"Debug session failed: {str(e)}", "error")

        # Summary
        duration = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 Debug Session Summary")
        print("=" * 60)
        print(f"Total time: {duration:.1f} seconds")
        print(f"Issues found: {len(self.issues_found)}")

        if self.issues_found:
            print("\n❌ Issues Found:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. [{issue['severity'].upper()}] {issue['issue']}")

            # Provide recommendations
            print("\n💡 Recommendations:")
            error_count = sum(1 for issue in self.issues_found if issue['severity'] == 'error')
            warning_count = len(self.issues_found) - error_count

            if error_count > 0:
                print("- Critical errors found that need immediate attention")
            if warning_count > 0:
                print("- Several warnings that may affect performance")

            print("- Consider increasing max_steps for complex web tasks")
            print("- BBC News website structure may have changed recently")
            print("- Browser automation may need enhanced action registry")

        else:
            print("✅ No issues found! System appears to be working correctly.")

        return len(self.issues_found) == 0


async def main():
    """Main debug function"""
    debugger = BBCNewsDebugger()
    success = await debugger.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Load environment if needed
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    asyncio.run(main())
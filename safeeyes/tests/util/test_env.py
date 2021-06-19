import unittest

from safeeyes.env.desktop import DesktopEnvironment


class DesktopEnvironmentTestCase(unittest.TestCase):

    def test_local_env(self):
        # This unit test is defined based on the development environment of Gobinath
        # It may fail if your development env is different
        env = DesktopEnvironment.get_env()
        self.assertEqual(env.name, "cinnamon")
        self.assertEqual(env.display_server, "xorg")


if __name__ == '__main__':
    unittest.main()

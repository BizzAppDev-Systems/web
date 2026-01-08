# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import Command
from odoo.tests import TransactionCase


class TestQuickStartActionsCommon(TransactionCase):
    def _test_screen_action(self, screen_action):
        """Basic test helper. For a more complete one we'd need a tour"""
        action = screen_action.run_action()
        if action["type"] == "ir.actions.server":
            action = (
                self.env.ref(action["xml_id"])
                .with_context(**screen_action._get_extra_context())
                .run()
            )
        return action


class TestQuickStartActions(TestQuickStartActionsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # Create actions
        cls.action_contacts = cls.env["quick.start.screen.action"].create(
            {
                "name": "Contacts",
                "description": "<span>Browse <b>contacts</b></span>",
                "action_ref_id": cls.env.ref("base.action_partner_form"),
                "icon_name": "fa-users",
                "color": 7,
            }
        )
        cls.action_access_rights = cls.env["quick.start.screen.action"].create(
            {
                "name": "Access rights",
                "description": "<span>Explore <b>access rights</b></span>",
                "action_ref_id": cls.env.ref("base.ir_access_act"),
                "icon_name": "fa-eye",
                "color": 4,
            }
        )
        cls.action_config = cls.env["quick.start.screen.action"].create(
            {
                "name": "Configure screen actions",
                "description": "<span>Configure this <b>screen actions</b></span>",
                "action_ref_id": cls.env.ref(
                    "web_quick_start_screen.quick_start_screen_action_action"
                ),
            }
        )
        # Create the screen
        cls.start_screen = cls.env["quick.start.screen"].create(
            {
                "name": "Test start screen",
                "action_ids": [
                    Command.link(cls.action_contacts.id),
                    Command.link(cls.action_config.id),
                ],
            }
        )
        # Create user and configure the screen
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Quick Start Test User",
                "login": "quickstart_test",
                "email": "quickstart@test.com",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref(
                            "web_quick_start_screen.group_quick_start_screen"
                        ).id
                    ),
                ],
                "quick_start_screen_id": cls.start_screen.id,
                "action_id": cls.env.ref(
                    "web_quick_start_screen.start_screen_action"
                ).id,
            }
        )

    def test_demo_screen_actions(self):
        """Let's test every action screen in our test data"""
        for action in self.test_user.quick_start_screen_id.action_ids:
            self._test_screen_action(action)

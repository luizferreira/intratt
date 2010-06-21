from unittest import TestSuite
from unittest import makeSuite

from Products.CMFCore.utils import getToolByName

from intranett.policy.tests.base import IntranettTestCase


class TestSiteSetup(IntranettTestCase):

    def test_installable_profiles(self):
        from Products.CMFPlone.browser.admin import AddPloneSite
        add = AddPloneSite(self.portal, self.portal.REQUEST)
        profiles = add.profiles()['extensions']
        ids = [p['id'] for p in profiles]
        self.assertEquals(ids, [u'intranett.policy:default'])

    def test_installable_products(self):
        qi = getToolByName(self.portal, 'portal_quickinstaller')
        installable = qi.listInstallableProducts()
        ids = [p['id'] for p in installable]
        self.assertEquals(ids, [])

    def test_PloneFormGen(self):
        tt = getToolByName(self.portal, 'portal_types')
        self.assert_('FormFolder' in tt.keys())

    def test_theme(self):
        skins = getToolByName(self.portal, 'portal_skins')
        self.assertEquals(skins.getDefaultSkin(), 'Sunburst Theme')

    def test_content(self):
        self.assertEquals(self.portal.contentIds(), ['Members'])

    def test_content_language(self):
        self.assertEquals(self.portal.Language(), 'no')

    def test_language_tool(self):
        tool = getToolByName(self.portal, "portal_languages")
        self.assertEquals(tool.getDefaultLanguage(), 'no')
        self.assertEquals(tool.supported_langs, ['no'])
        self.assertEquals(tool.display_flags, 0)
        self.assertEquals(tool.start_neutral, 0)
        self.assertEquals(tool.use_combined_language_codes, 0)

    def test_locale(self):
        calendar = getToolByName(self.portal, "portal_calendar")
        # Make sure we have Monday
        self.assertEquals(calendar.firstweekday, 0)


class TestAdmin(IntranettTestCase):

    def test_overview(self):
        self.loginAsPortalOwner()
        overview = self.app.unrestrictedTraverse('@@plone-overview')
        result = overview()
        self.assert_('View your intranet' in result, result)

    def test_addsite_profiles(self):
        self.loginAsPortalOwner()
        addsite = self.app.unrestrictedTraverse('@@intranett-addsite')
        extensions = addsite.profiles()['extensions']
        self.assertEquals(len(extensions), 1)
        profile = extensions[0]
        self.assertEquals(profile['id'], u'intranett.policy:default')


def test_suite():
    return TestSuite([
        makeSuite(TestSiteSetup),
        makeSuite(TestAdmin),
    ])

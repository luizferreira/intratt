import os

from plone.app.testing import TEST_USER_ID
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletType
from plone.portlets.manager import PortletManager
from Products.CMFCore.utils import getToolByName
from zope.component import getSiteManager
from zope.component import queryUtility

from intranett.policy.upgrades import steps
from intranett.policy.tests.upgrade import FunctionalUpgradeTestCase


class TestUpgradeSteps(FunctionalUpgradeTestCase):

    def test_update_caching_config(self):
        portal = self.layer['portal']
        registry = getToolByName(portal, 'portal_registry')
        purge_key = 'plone.app.caching.interfaces.IPloneCacheSettings.' \
            'purgedContentTypes'
        etag_key = 'plone.app.caching.weakCaching.etags'
        registry.records[purge_key].value = ('Document', )
        registry.records[etag_key].value = ('userid', 'language', )
        steps.update_caching_config(portal)
        self.assertEqual(registry.records[purge_key].value,
            ('File', 'Image', 'News Item'))
        self.assertTrue('editbar' in registry.records[etag_key].value)

    def test_migrate_portraits(self):
        from OFS.Image import Image
        from intranett.policy.tests.test_userdata import TEST_IMAGES
        from intranett.policy.tests.utils import make_file_upload
        from intranett.policy.tools import Portrait

        portal = self.layer['portal']

        mdt = getToolByName(portal, 'portal_memberdata')
        path = os.path.join(TEST_IMAGES, 'test.jpg')
        image_jpg = make_file_upload(path, 'image/jpeg', 'myportrait.jpg')

        image = Image(id=TEST_USER_ID, file=image_jpg, title='')
        thumb = Image(id=TEST_USER_ID, file=image_jpg, title='')
        mdt._setPortrait(image, TEST_USER_ID)
        mdt._setPortrait(thumb, TEST_USER_ID, thumbnail=True)

        steps.migrate_portraits(portal)

        self.assertTrue(TEST_USER_ID in mdt.portraits)
        self.assertTrue(TEST_USER_ID in mdt.thumbnails)
        self.assertTrue(isinstance(mdt.portraits[TEST_USER_ID], Portrait))
        self.assertTrue(isinstance(mdt.thumbnails[TEST_USER_ID], Portrait))

    def test_disable_webstats_js(self):
        portal = self.layer['portal']
        ptool = getToolByName(portal, 'portal_properties')
        sprops = ptool.site_properties
        sprops.webstats_js = '<script type="text/javascript" />'
        steps.disable_webstats_js(portal)
        self.assertEqual(sprops.webstats_js, '')

    def test_remove_unused_frontpage_portlets(self):
        portal = self.layer['portal']
        sm = getSiteManager()
        names = ('frontpage.portlets.left', 'frontpage.portlets.central',
            'frontpage.bottom')
        def create_pm(name):
            sm.registerUtility(component=PortletManager(),
                provided=IPortletManager, name=name)
        for name in names:
            create_pm(name)
        steps.remove_unused_frontpage_portlets(portal)
        registrations = [r.name for r in sm.registeredUtilities()
                         if IPortletManager == r.provided]
        self.assertFalse('frontpage.portlets.left' in registrations)
        self.assertFalse('frontpage.portlets.central' in registrations)
        self.assertFalse('frontpage.bottom' in registrations)

    def test_add_site_administrator(self):
        portal = self.layer['portal']
        existing_roles = set(getattr(portal, '__ac_roles__', []))
        existing_roles.remove('Site Administrator')
        portal.__ac_roles__ = tuple(existing_roles)
        steps.add_site_administrator(portal)
        existing_roles = set(getattr(portal, '__ac_roles__', []))
        self.assertIn('Site Administrator', existing_roles)

    def test_allow_site_admin_to_edit_frontpage(self):
        from plone.app.portlets.interfaces import IColumn
        portal = self.layer['portal']
        setattr(portal, '_Portlets__Manage_portlets_Permission', ['Manager'])
        fti = getToolByName(portal, 'portal_types')['Plone Site']
        edit_action = [a for a in fti.listActions() if a.id == 'edit-frontpage']
        edit_action[0].permissions = ('Manage portal', )
        coll_id = u'plone.portlet.collection.Collection'
        coll = queryUtility(IPortletType, name=coll_id)
        coll.for_ = [IColumn]
        steps.allow_site_admin_to_edit_frontpage(portal)
        perms = set(getattr(portal, '_Portlets__Manage_portlets_Permission'))
        self.assertEqual(perms, set(['Manager', 'Site Administrator']))
        self.assertEqual(edit_action[0].permissions,
            (u'Portlets: Manage portlets', ))
        self.assertEqual(coll.for_, [])

    def test_allow_member_to_edit_personal_portlets(self):
        portal = self.layer['portal']
        perm_id = '_plone_portlet_static__Add_static_portlet_Permission'
        setattr(portal, perm_id, ['Manager'])
        steps.allow_member_to_edit_personal_portlets(portal)
        self.assertEqual(set(getattr(portal, perm_id)),
            set(['Manager', 'Member', 'Site Administrator']))

    def test_add_frontpage_cacherule(self):
        from plone.caching.interfaces import ICacheSettings
        from plone.registry.interfaces import IRegistry
        portal = self.layer['portal']
        steps.add_frontpage_cacherule(portal)
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(ICacheSettings)
        value = settings.operationMapping['intranett.frontpage']
        self.assertEqual(value, 'plone.app.caching.noCaching')

    def test_change_frontpage_portlets(self):
        portal = self.layer['portal']
        sm = getSiteManager()
        sm.registerUtility(component=PortletManager(),
            provided=IPortletManager, name='frontpage.highlight')
        steps.change_frontpage_portlets(portal)
        registrations = [r.name for r in sm.registeredUtilities()
                         if IPortletManager == r.provided]
        self.assertFalse('frontpage.highlight' in registrations)
        self.assertTrue('frontpage.main.top' in registrations)

    def test_allow_siteadmin_to_edit_content(self):
        portal = self.layer['portal']
        perm_id = '_ATContentTypes__Add_Folder_Permission'
        setattr(portal, perm_id, ['Manager'])
        steps.allow_siteadmin_to_edit_content(portal)
        self.assertEqual(set(getattr(portal, perm_id)),
            set(['Manager', 'Contributor', 'Site Administrator', 'Owner']))

    def test_highlight_portlets_available(self):
        portal = self.layer['portal']
        prefix = '++resource++plone.formwidget.autocomplete/jquery.' \
            'autocomplete'
        css = getToolByName(portal, 'portal_css')
        css.unregisterResource(prefix + '.css')
        js = getToolByName(portal, 'portal_javascripts')
        js.unregisterResource(prefix + '.min.js')
        sm = getSiteManager()
        sm.unregisterUtility(provided=IPortletType,
            name='intranett.policy.portlets.NewsHighlight')
        sm.unregisterUtility(provided=IPortletType,
            name='intranett.policy.portlets.EventHighlight')
        regs = [r.name for r in sm.registeredUtilities()
            if r.provided == IPortletType]
        # call the upgrade step
        steps.install_highlight_portlets(portal)
        regs = [r.name for r in sm.registeredUtilities()
            if r.provided == IPortletType]
        self.assertTrue('intranett.policy.portlets.NewsHighlight' in regs)
        self.assertTrue('intranett.policy.portlets.EventHighlight' in regs)
        self.assertTrue(prefix + '.css' in css.getResourcesDict().keys())
        self.assertTrue(prefix + '.min.js' in js.getResourcesDict().keys())

    def test_deactivate_collective_flag(self):
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
        portal = self.layer['portal']
        atct = getToolByName(portal, 'portal_atct')
        atct.addIndex('flaggedobject')
        catalog = getToolByName(portal, 'portal_catalog')
        catalog._catalog.addIndex('flaggedobject', FieldIndex('flaggedobject'))
        steps.deactivate_collective_flag(portal)
        self.assertFalse('flaggedobject' in atct.getIndexes())
        self.assertFalse('flaggedobject' in catalog.indexes())

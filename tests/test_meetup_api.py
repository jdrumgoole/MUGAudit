# -*- coding: utf-8 -*-
'''
Created on 26 Nov 2016

@author: jdrumgoole
'''
import unittest
from mugalyser.meetup_api import MeetupAPI
from mugalyser.apikey import get_meetup_key
import types
from datetime import datetime

class Test_meetup_api(unittest.TestCase):
        
    def setUp(self):
        apikey = get_meetup_key()
        self._api = MeetupAPI( apikey, reshape=True  )
    
    def tearDown(self):
        pass

    def test_get_group( self):
        
        g = self._api.get_group( "DublinMUG" )
        self.assertTrue( "city" in g and g["city"] == u"Dublin" )
        self.assertTrue( "timezone" in g and g[ "timezone" ] == u"Europe/Dublin")
        self.assertTrue( g[ "urlname"] == u"DublinMUG")
        self.assertTrue( g[ "id" ] == 3478392 )
        self.assertTrue( g[ "country" ] == u"IE" )
        #pprint.pprint( g )
        self.assertTrue( "location"  in g )
        self.assertTrue( g.has_key( "created" ))
        
    def test_get_pro_groups(self):
        
        g = self._api.get_pro_groups()
        count = 0
        for  i in g:

            self.assertTrue( "rsvps_per_event" in i )
            self.assertTrue( "pro_join_date" in i )
            self.assertTrue( "founded_date" in i )
            self.assertTrue( isinstance( i[ "pro_join_date" ], datetime ))
            self.assertTrue( isinstance( i[ "founded_date" ], datetime ))
            count = count + 1 
            
        self.assertGreaterEqual( count, 116 )
            
    def test_get_past_events(self ):
        
        g = self._api.get_past_events("DublinMUG" )
        events = list( g )
        self.assertGreaterEqual( len( events ), 29 )

        event = events[ 0 ]
        
        #self.assertEqual( event[ "created"], 1335802792000 )
        self.assertEqual( event[ "event_url"], u'https://www.meetup.com/DublinMUG/events/62760772/' )
        self.assertTrue( isinstance( event[ "created"], datetime ))
                         
    def test_get_all_attendees( self ):
        attendees = self._api.get_all_attendees( [ "DublinMUG", "London-MongoDB-User-Group" ] )
        attendees = list( attendees )
        self.assertGreaterEqual(len( attendees ), 1306 )
        ( attendee, event )  = attendees[ 0 ]
        self.assertTrue( u"member" in attendee )
        self.assertTrue( u"rsvp" in attendee )
        self.assertTrue( u"status" in attendee )
        
        self.assertTrue( u"announced" in event )
        self.assertTrue( u"group" in event )
        self.assertTrue( u"name" in event )
        self.assertEqual( event[ "rsvp_limit"], 80 )

    def test_get_member_by_id(self):
        member = self._api.get_member_by_id( 210984049 )
        self.assertEqual( member[ "name"], u"Julio Román" )
        #print( member[ "name"] )
        self.assertEqual( type(member[ "name"] ), types.UnicodeType )
        
    def test_get_member_by_url(self):
        
        members = self._api.get_members( [ "DublinMUG", "London-MongoDB-User-Group"])
        self.assertGreaterEqual( ( sum( 1 for _ in  members )), 2465 )
        
    def test_get_members(self ):
        
        members = self._api.get_members( ["DublinMUG" ] )
        count = 0
        for _ in members:
            count = count + 1 
            #print( "%i %s" % (count, i ))
            #print( i )
        self.assertGreaterEqual( count,  844 )
        
        members = list( self._api.get_pro_members())
        self.assertGreaterEqual( ( sum( 1 for _ in  members )) , 17400 )
        
        

            
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
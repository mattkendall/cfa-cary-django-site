# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PermitArea'
        db.create_table(u'permit_map_permitarea', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('region', self.gf('django.contrib.gis.db.models.fields.MultiPolygonField')()),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('township', self.gf('django.db.models.fields.CharField')(max_length=4)),
            ('first_seen', self.gf('django.db.models.fields.DateField')()),
            ('last_seen', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal(u'permit_map', ['PermitArea'])

        # Adding model 'PermitData'
        db.create_table(u'permit_map_permitdata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(related_name='data', to=orm['permit_map.PermitArea'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True)),
            ('proj_id', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True)),
            ('link', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True)),
            ('saved_on', self.gf('django.db.models.fields.DateField')()),
            ('search_index', self.gf('djorm_pgfulltext.fields.VectorField')(default='', null=True, db_index=True)),
        ))
        db.send_create_signal(u'permit_map', ['PermitData'])


    def backwards(self, orm):
        # Deleting model 'PermitArea'
        db.delete_table(u'permit_map_permitarea')

        # Deleting model 'PermitData'
        db.delete_table(u'permit_map_permitdata')


    models = {
        u'permit_map.permitarea': {
            'Meta': {'object_name': 'PermitArea'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'first_seen': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_seen': ('django.db.models.fields.DateField', [], {}),
            'region': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'township': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        u'permit_map.permitdata': {
            'Meta': {'object_name': 'PermitData'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data'", 'to': u"orm['permit_map.PermitArea']"}),
            'proj_id': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'}),
            'saved_on': ('django.db.models.fields.DateField', [], {}),
            'search_index': ('djorm_pgfulltext.fields.VectorField', [], {'default': "''", 'null': 'True', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True'})
        }
    }

    complete_apps = ['permit_map']
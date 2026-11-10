"""Shared-parent information needs and explicit evidence deliveries.

Records are immutable canonical Sources, indexed in the existing Store. A need
is an operational request, not scientific evidence. Publishing metadata does
not grant another episode access to the referenced scientific records.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, identity, obj
from .episode_return_records import EpisodeReturnRecords
from .shared_information_results import publication_view


VERSION = 'shared_investigation_information_v4'
PARTICIPANT_ROLES = frozenset({'annotation', 'scientific_process', 'improvement'})
DISPOSITIONS = ('partially_fulfilled', 'fulfilled', 'unavailable', 'superseded')
TOOLS = ('shared.request_information','shared.publish_information',
    'shared.resolve_information_need','shared.read_information','shared.list_information')


def catalog():
    text={'type':'string','minLength':1}
    reference={'type':'string','format':'reference'}
    references={'type':'array','items':reference,'uniqueItems':True}
    disposition = obj({'need_ref':reference,'status':{'type':'string','enum':list(DISPOSITIONS)},
        'evidence_refs':references,'reason':{**text,
            'description':'Operational reason for unavailable or superseded information. Evidence results and qualifications come from saved grading, not a rewritten assessment.'}},
        required=['need_ref','status','evidence_refs'])
    disposition['allOf'] = [{'if':{'properties':{'status':{'enum':['unavailable','superseded']}}},
        'then':{'required':['reason']},'else':{'not':{'required':['reason']}}}]
    return [
        {'name':TOOLS[0],'description':'Send this episode\'s immediate participating parent a specific missing operand and the decision it affects. State source, subject and provenance requirements and whether the assigned result depends on it. Publication commissions no work, promises no reply and is not a reason to wait; preserve the limitation in the requested child return.',
         'input_schema':obj({'target_ref':reference,'question':text,'required_information':text,
             'reason':text,'blocking':{'type':'boolean'},'available_record_refs':references})},
        {'name':TOOLS[1],'description':'Offer the immediate participating parent selected evidence already received and within scope. Select the actual saved grading or scoring-sheet records when offering graded results. The host displays their existing saved values, conditions and limitations after receipt; supply no additional evidence assessment. Your exchange preview names the records you have already offered. Reuse an existing equivalent offer; publishing the same record set again adds no information or evidence credit. The result identifies equivalent prior offers, not parent receipt. This offer does not replace the requested child form or admit evidence to the parent.',
         'input_schema':obj({'target_ref':reference,'evidence_refs':references})},
        {'name':TOOLS[2],'description':'Answer a need addressed to this parent by selecting evidence it actually received. Fulfilled and partially fulfilled replies carry saved results and their qualifications through the receipt boundary without an additional assessment paragraph. For unavailable or superseded information, supply the operational reason. Further investigations are separate iterator choices; this operation cannot assign work.',
         'input_schema':disposition},
        {'name':TOOLS[3],'description':'Read one publication from the displayed parent/child exchange. An evidence offer or response delivers exactly its selected evidence references through the normal receipt boundary; a need delivers its metadata only. The receiver\'s existing readers, subscoring sheets and credit projection assess any acquired evidence.',
         'input_schema':obj({'publication_ref':reference})},
        {'name':TOOLS[4],'description':'Page existing parent/child exchange metadata omitted from the automatic preview. This is historical navigation, not polling for a promised reply, and delivers no scientific evidence.',
            'input_schema':obj({'kind':{'enum':['all','need','information','disposition']},
                'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':24}})},
    ]


class SharedInformation:
    def __init__(self, store, run_id):
        self.store,self.run_id=store,run_id
        self.records=EpisodeReturnRecords(store,run_id,failure_prefix='shared_information_')
        store.db.execute('''CREATE TABLE IF NOT EXISTS shared_investigation_publications (
                source_ref TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                path TEXT NOT NULL, scope TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL)''')
        store.db.execute('''CREATE TABLE IF NOT EXISTS shared_investigation_operations (
                operation_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                request TEXT NOT NULL, result TEXT NOT NULL)''')

    def _participant(self, episode_id):
        return identity('shared_participant',{'run_id':self.run_id,'episode_id':episode_id})

    def _authenticate(self, context):
        self.records.authenticate(context)
        if context.role not in PARTICIPANT_ROLES:
            raise ContractError('shared_information_requires_scientific_or_parent_role')

    def parent(self, context, *, require_active=False):
        """Resolve a real immediate receiver, never an imagined root parent.

        Nonparticipating intermediate episodes retain their ordinary typed
        return boundary; this channel does not bypass them to reach a root.
        """
        self._authenticate(context)
        if len(context.path) < 2 or context.path[-2][0] not in PARTICIPANT_ROLES:
            return None
        from method_loop.identities import EpisodeRef
        parent = self.records.context(EpisodeRef(self.run_id, context.path[:-1]).episode_id)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(parent.scope))
        if require_active and self._episode_state(parent.episode_id) != 'active':
            return None
        return parent

    def _recipient(self, row, body):
        if body.get('recipient_participant_ref') is not None:
            return body['recipient_participant_ref']
        if row['kind'] == 'disposition':
            return body.get('requester_participant_ref')
        # Earlier records did not name a recipient. Their actual immediate
        # parent is recoverable; arbitrary ancestors are not recipients.
        owner = self.records.context(row['episode_id'])
        parent = self.parent(owner)
        return None if parent is None else self._participant(parent.episode_id)

    def _visible(self, context, row, body):
        return (row['episode_id'] == context.episode_id
            or self._recipient(row, body) == self._participant(context.episode_id))

    def _episode_state(self, episode_id):
        columns = {row[1] for row in self.store.db.execute('PRAGMA table_info(runtime_episodes)')}
        if 'state' not in columns:
            return 'unknown'
        row = self.store.db.execute('SELECT state FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, episode_id)).fetchone()
        return 'unknown' if row is None else row['state']

    def catalog(self, context):
        """Expose only routes with an existing receiver or readable message."""
        self._authenticate(context)
        names = set(TOOLS[:2]) if self.parent(context, require_active=True) is not None else set()
        view = self.context_view(context, _unbounded=True)
        publications = [item for name in ('needs', 'information_available', 'dispositions')
                        for item in view[name]]
        if publications:
            names.add(TOOLS[3])
        if any(need['recipient_participant_ref'] == self._participant(context.episode_id)
                and need['requester_state'] == 'active'
                for need in view['needs']):
            names.add(TOOLS[2])
        if max(view['total_needs'], view['total_information'], view['total_dispositions']) > 24:
            names.add(TOOLS[4])
        return [entry for entry in catalog() if entry['name'] in names]

    def _target(self, context, reference):
        target=self.store.get(reference)
        scoped_root=reference in plain(context.scope)['subject_refs']
        if target['record_type'] not in {'input','feature','product','read_subject'} or not (scoped_root or self.store.scope_covers(
                self.store.coverage(reference),plain(context.scope))):
            raise ContractError('shared_information_target_outside_scope')

    def _eligible(self, context, references, known):
        if set(references)-set(known):
            raise ContractError('shared_information_evidence_not_received')
        if set(self.store.reference_subset(references,plain(context.scope)))!=set(references):
            raise ContractError('shared_information_evidence_outside_scope')

    def _row(self, reference):
        row=self.store.db.execute('SELECT * FROM shared_investigation_publications WHERE source_ref=? '
            'AND run_id=?',(reference,self.run_id)).fetchone()
        if row is None:raise ContractError('shared_information_publication_unavailable')
        body=json.loads(row['body'])
        source=self.store.get(reference)
        if (source['record_type']!='source' or source['origin']!='tool'
                or source['provider']!='episode.shared_information'
                or json.loads(self.store.get_artifact(source['artifact_ref']))!=body):
            raise ContractError('shared_information_publication_custody_conflict')
        return row,body

    def _publish(self, context, kind, body, operation_key):
        value={'version':VERSION,'kind':kind,'producer_participant_ref':self._participant(context.episode_id),
            'scope':plain(context.scope),**deepcopy(body)}
        artifact=self.store.artifact(canonical(value),'application/json')
        source=self.store.put('source',{'provider':'episode.shared_information',
            'accession':identity('shared_publication',{'run_id':self.run_id,'operation_key':operation_key}),
            'uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
            'version':VERSION,'retrieved_at':None},origin='tool')['id']
        self.store.db.execute('INSERT INTO shared_investigation_publications VALUES(?,?,?,?,?,?,?)',
            (source,self.run_id,context.episode_id,canonical(plain(context.path)),
             canonical(value['scope']),kind,canonical(value)))
        return {'status':'completed','record_refs':[source],'changed_record_refs':[],
            'result':{'publication_ref':source,**value},'feedback':None}

    def _offer_history(self, context, body):
        """Describe this producer's exact earlier offers, without granting evidence."""
        count, first = 0, None
        selected = set(body['evidence_refs'])
        for row in self.store.db.execute('SELECT * FROM shared_investigation_publications '
                "WHERE run_id=? AND episode_id=? AND kind='information' AND scope=? ORDER BY rowid",
                (self.run_id, context.episode_id, canonical(plain(context.scope)))):
            earlier = json.loads(row['body'])
            if (earlier.get('target_ref') == body['target_ref']
                    and self._recipient(row, earlier) == body['recipient_participant_ref']
                    and set(earlier.get('evidence_refs', [])) == selected):
                count += 1
                if first is None:
                    first = row['source_ref']
        return {'equivalent_prior_offer_count': count,
            'first_equivalent_publication_ref': first,
            'meaning': 'Same selected records, target, scope and recipient; '
                'metadata publication does not establish parent receipt or new scientific information.'}

    def _evidence_metadata(self, references):
        """Name offered record types without disclosing unreceived science."""
        result = []
        for reference in references:
            record = self.store.get(reference)
            fields = ['record_type', 'provider', 'version']
            if record['record_type'] in {'source', 'input', 'feature', 'product', 'read_subject'}:
                fields.extend(('label', 'title', 'name'))
            metadata = {key: record[key] for key in fields if record.get(key) is not None}
            if metadata not in result:
                result.append(metadata)
        return result

    def execute(self, context, name, arguments, *, known_record_refs, operation_key):
        self._authenticate(context)
        if name not in TOOLS:raise ContractError('shared_information_operation_unavailable')
        request=canonical({'name':name,'arguments':arguments})
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM shared_investigation_operations WHERE operation_key=?',
                (operation_key,)).fetchone()
            if old is not None:
                if (old['run_id'],old['episode_id'],old['request'])!=(self.run_id,context.episode_id,request):
                    raise ContractError('shared_information_operation_identity_conflict')
                return json.loads(old['result'])
            from .domain import validate_schema
            schema=next(row['input_schema'] for row in catalog() if row['name']==name)
            validate_schema(arguments,schema)
            if name==TOOLS[0]:
                parent = self.parent(context, require_active=True)
                if parent is None:
                    raise ContractError('shared_information_parent_recipient_unavailable')
                self._target(context,arguments['target_ref'])
                self._eligible(context,arguments['available_record_refs'],known_record_refs)
                result=self._publish(context,'need',{
                    **arguments,'recipient_participant_ref':self._participant(parent.episode_id)},operation_key)
            elif name==TOOLS[1]:
                parent = self.parent(context, require_active=True)
                if parent is None:
                    raise ContractError('shared_information_parent_recipient_unavailable')
                self._target(context,arguments['target_ref'])
                if not arguments['evidence_refs']:raise ContractError('shared_information_evidence_required')
                self._eligible(context,arguments['evidence_refs'],known_record_refs)
                body={**arguments,'recipient_participant_ref':self._participant(parent.episode_id)}
                history=self._offer_history(context, body)
                result=self._publish(context,'information',body,operation_key)
                result['result']['offer_history']=history
            elif name==TOOLS[2]:
                row,need=self._row(arguments['need_ref'])
                if (row['kind']!='need'
                        or self._recipient(row,need)!=self._participant(context.episode_id)):
                    raise ContractError('shared_information_need_resolution_owned_by_parent')
                if self._episode_state(row['episode_id']) != 'active':
                    raise ContractError('shared_information_requester_not_active_use_next_commission')
                self.store.validate_scope(need['scope'],parent_scope=plain(context.scope))
                self._eligible(context,arguments['evidence_refs'],known_record_refs)
                if set(self.store.reference_subset(arguments['evidence_refs'],need['scope']))!=set(arguments['evidence_refs']):
                    raise ContractError('shared_information_delivery_outside_request_scope')
                if arguments['status'] in {'fulfilled','partially_fulfilled'} and not arguments['evidence_refs']:
                    raise ContractError('shared_information_fulfillment_requires_evidence')
                result=self._publish(context,'disposition',{'target_ref':need['target_ref'],
                    'scope':need['scope'],'requester_participant_ref':self._participant(row['episode_id']),
                    'recipient_participant_ref':self._participant(row['episode_id']),**arguments},operation_key)
            elif name==TOOLS[3]:
                row,body=self._row(arguments['publication_ref'])
                if not self._visible(context,row,body):
                    raise ContractError('shared_information_delivery_not_authorized')
                self.store.validate_scope(body['scope'],parent_scope=plain(context.scope))
                evidence=body.get('evidence_refs',[]) if row['kind'] in {'information','disposition'} else []
                result={'status':'completed','record_refs':list(dict.fromkeys([row['source_ref'],*evidence])),
                    'changed_record_refs':[],'result':{'publication_ref':row['source_ref'],
                        **publication_view(body)},'feedback':None}
            else:
                view=self.context_view(context,_unbounded=True)
                if max(view['total_needs'],view['total_information'],view['total_dispositions'])<=24:
                    raise ContractError('shared_information_metadata_page_unavailable')
                rows=[row for key in ('needs','information_available','dispositions') for row in view[key]
                    if arguments['kind']=='all' or row['kind']==arguments['kind']]
                rows.sort(key=lambda row:row['publication_ref'])
                start,limit=arguments['offset'],arguments['limit']
                result={'status':'completed','record_refs':[],'changed_record_refs':[],
                    'result':{'metadata':rows[start:start+limit],'total':len(rows),
                        'next_query':{**arguments,'offset':start+limit} if start+limit<len(rows) else None},'feedback':None}
            self.store.db.execute('INSERT INTO shared_investigation_operations VALUES(?,?,?,?,?)',
                (operation_key,self.run_id,context.episode_id,request,canonical(result)))
            return result

    def context_view(self, context, *, _unbounded=False):
        """Show the current decision-relevant exchange, without source bodies."""
        self._authenticate(context)
        needs,information,dispositions=[],[],[]
        for row in self.store.db.execute('SELECT * FROM shared_investigation_publications '
                'WHERE run_id=? ORDER BY rowid',(self.run_id,)):
            body=json.loads(row['body'])
            if not self._visible(context,row,body):continue
            try:self.store.validate_scope(body['scope'],parent_scope=plain(context.scope))
            except (ValueError,ContractError):continue
            common = ('kind','producer_participant_ref','target_ref','scope')
            fields = {'need': ('question','required_information','reason','blocking'),
                'information': (),
                'disposition': ('need_ref','status','reason','requester_participant_ref')}[row['kind']]
            body = publication_view(body)
            value={'publication_ref':row['source_ref'],
                **{name:body[name] for name in (*common,*fields) if name in body},
                'recipient_participant_ref':self._recipient(row,body)}
            if row['kind'] in {'information','disposition'}:
                value['evidence_count']=len(body.get('evidence_refs',[]))
                value['offered_material']=self._evidence_metadata(body.get('evidence_refs',[]))
                if row['kind']=='information' and row['episode_id']==context.episode_id:
                    # The producer selected and already knew these references.
                    # A recipient still sees metadata only until an explicit read.
                    value['offered_evidence_refs']=list(body.get('evidence_refs',[]))
            else:
                value['available_record_count']=len(body.get('available_record_refs',[]))
                value['requester_state']=self._episode_state(row['episode_id'])
                value['response_route']=('parent_recipient_unavailable'
                    if value['recipient_participant_ref'] is None else
                    'existing_requester' if value['requester_state']=='active'
                    else 'retained_limitation_for_parent_next_commission')
            if row['kind']=='need':needs.append(value)
            elif row['kind']=='information':information.append(value)
            else:dispositions.append(value)
        latest={row['need_ref']:row for row in dispositions}
        for need in needs:
            resolved=latest.get(need['publication_ref'])
            need['status']=('recipient_unavailable' if need['recipient_participant_ref'] is None
                else 'open') if resolved is None else resolved['status']
            need['disposition_ref']=None if resolved is None else resolved['publication_ref']
            need['response_work']='no_response_work_commissioned_by_this_publication'
            if resolved is not None and 'reason' in resolved:
                need['disposition_reason']=resolved['reason']
        # The latest disposition is enough to steer; older versions remain in
        # immutable Sources and the explicitly requested metadata page.
        total_dispositions=len(dispositions)
        if not _unbounded:
            dispositions=list(latest.values())
        parent=self.parent(context, require_active=True)
        return {'version':VERSION,'needs':needs if _unbounded else needs[-24:],
            'information_available':information if _unbounded else information[-24:],
            'dispositions':dispositions if _unbounded else dispositions[-24:],'total_needs':len(needs),
            'total_information':len(information),'total_dispositions':total_dispositions,
            'older_metadata_query':{'kind':'all','offset':0,'limit':24}
                if max(len(needs),len(information),total_dispositions)>24 else None,
            'upward_recipient':None if parent is None else {
                'participant_ref':self._participant(parent.episode_id),'role':parent.role},
            'authority':'Metadata publication does not admit referenced scientific evidence. '
                'Read an offered source or response explicitly; its existing readers and subscoring sheets '
                'retain their authority. Evidence results and qualifications are copied from saved grading '
                'or scoring sheets after receipt and reported with the original read action and earned credit; '
                'no additional evidence-summary paragraph is requested. Needs go to the immediate participating parent, which may '
                'supply received evidence, select work from its own options, or relay a specific need '
                'to its parent. Publication alone starts no work, promises no reply and does not justify '
                'waiting. Preserve unmet needs as limitations in the requested typed return.'}

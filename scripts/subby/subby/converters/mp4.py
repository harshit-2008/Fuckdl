from collections import deque

from pymp4.parser import MP4
from pymp4.util import BoxUtil

from subby.converters.base import BaseConverter
from subby.converters.smpte import SMPTEConverter
from subby.converters.webvtt import WebVTTConverter
from subby.subripfile import SubRipFile
from subby.utils.time import timestamp_from_ms

from abc import ABC, abstractmethod


class BaseSegmentedConverter(BaseConverter, ABC):
    """Segmented stream base converter"""

    def parse(self, stream):
        ftyp_box_header = b"\x00\x00\x00\x1cftyp"
        styp_box_header = b"\x00\x00\x00\x18styp"

        data = stream.read()
        first_segment_position = data.find(styp_box_header)

        segments = []
        if first_segment_position >= 0:
            position = data.find(ftyp_box_header)
            if position < 0:
                # Init not found in segmented data - timescale is likely incorrect.
                position = 0
            previous_position = position
            while True:
                position = data.find(styp_box_header, position)
                if position < 0:
                    break
                segment = data[previous_position:position]
                segments.append(segment)
                previous_position = position
                position += len(segment)
            # Add the last segment
            if previous_position < len(data):
                segments.append(data[previous_position:])
        else:
            segments.append(data)

        return self._parse(segments)

    @abstractmethod
    def _parse(self, segments) -> SubRipFile:
        ...


class ISMTConverter(BaseSegmentedConverter):
    """ISMT (DFXP in MP4) subtitle converter"""

    def _parse(self, segments):
        srt = SubRipFile([])

        for segment in segments:
            for box in MP4.parse(segment):
                if box.type == b'mdat':
                    new = SMPTEConverter().from_bytes(box.data)

                    # Offset timecodes if necessary
                    # https://github.com/SubtitleEdit/subtitleedit/blob/abd36e5/src/libse/SubtitleFormats/IsmtDfxp.cs#L85-L90
                    if srt and new and srt[-1].start > new[0].start:
                        new.offset(srt[-1].end)

                    srt.extend(new)

        return srt


class WVTTConverter(BaseSegmentedConverter):
    """WVTT (WebVTT in MP4) subtitle converter"""
    
    def _parse(self, segments):
        vtt_lines = []
        timescale = 10000  # Default timescale

        for segment in segments:
            try:
                boxes = list(MP4.parse(segment))
            except:
                continue
            
            # Collect timing info for this segment
            sample_durations = deque()
            
            for box in boxes:
                if box.type == b'moov':
                    for mdhd in BoxUtil.find(box, b'mdhd'):
                        timescale = mdhd.timescale
                        break

                    for stsd in BoxUtil.find(box, b'stsd'):
                        if stsd.entries:
                            wvtt = stsd.entries[0]
                            for child in wvtt.children:
                                if child.type == b'vttC':
                                    header = child.config
                                    vtt_lines.append(f'{header}\n\n')
                                    break
                        break

                if box.type == b'moof':
                    start_offset = 0
                    
                    for tfdt in BoxUtil.find(box, b'tfdt'):
                        start_offset = tfdt.baseMediaDecodeTime
                        break

                    for trun in BoxUtil.find(box, b'trun'):
                        if hasattr(trun, 'sample_info') and trun.sample_info:
                            current_time = start_offset
                            for sample in trun.sample_info:
                                duration = getattr(sample, 'sample_duration', 0) or 0
                                
                                start_ms = (current_time / timescale) * 1000
                                end_ms = ((current_time + duration) / timescale) * 1000
                                
                                sample_durations.append({
                                    'start_ms': start_ms,
                                    'end_ms': end_ms
                                })
                                
                                current_time += duration

            # Now process mdat boxes for this segment
            for box in boxes:
                if box.type == b'mdat':
                    try:
                        vtt_boxes = list(MP4.parse(box.data))
                    except:
                        continue
                        
                    new_start = None
                    
                    for vtt_box in vtt_boxes:
                        # Get settings
                        settings = ""
                        for sttg in BoxUtil.find(vtt_box, b'sttg'):
                            settings = sttg.settings
                            break

                        # Get cue text
                        cue_text = None
                        for payl in BoxUtil.find(vtt_box, b'payl'):
                            cue_text = payl.cue_text
                            break

                        # Get timing
                        try:
                            sample_duration = sample_durations.popleft()
                        except IndexError:
                            # No durations found, skip
                            continue

                        if vtt_box.type == b'vttc':
                            # Regular cue
                            if new_start is not None:
                                start_ms = new_start
                                new_start = None
                            else:
                                start_ms = sample_duration['start_ms']
                            
                            end_ms = sample_duration['end_ms']

                            if cue_text is not None:
                                vtt_lines.append(
                                    f'{timestamp_from_ms(start_ms)} --> '
                                    f'{timestamp_from_ms(end_ms)} '
                                    f'{settings}\n{cue_text}\n\n'
                                )
                                
                        elif vtt_box.type == b'vtte':
                            # Empty cue - marks a gap, next cue starts here
                            new_start = sample_duration['end_ms']

        return WebVTTConverter().from_string(''.join(vtt_lines))
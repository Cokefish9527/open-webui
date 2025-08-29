import logging
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageOps
import cv2
import magic
from moviepy.editor import VideoFileClip
import wave
import json
import time

log = logging.getLogger(__name__)


class HSAIFileProcessor:
    """HSAI文件处理器，提供文件上传、分析、缩略图生成等功能"""
    
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.thumbnails_dir = self.upload_dir / "thumbnails"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的文件类型
        self.supported_types = {
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.md'],
            'other': []
        }
        
        # 缩略图配置
        self.thumbnail_config = {
            'image': {'size': (300, 300), 'quality': 85},
            'video': {'size': (300, 200), 'frame_time': 1.0},  # 取第1秒的帧
            'document': {'size': (200, 280)},
            'audio': {'size': (200, 200)}  # 音频使用默认图标
        }
    
    def get_file_type(self, filename: str) -> str:
        """根据文件扩展名判断文件类型"""
        ext = Path(filename).suffix.lower()
        
        for file_type, extensions in self.supported_types.items():
            if ext in extensions:
                return file_type
        
        return 'other'
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def get_file_mime_type(self, file_path: Path) -> str:
        """获取文件MIME类型"""
        try:
            # 使用python-magic获取更准确的MIME类型
            mime = magic.Magic(mime=True)
            return mime.from_file(str(file_path))
        except:
            # 回退到mimetypes
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or 'application/octet-stream'
    
    def extract_metadata(self, file_path: Path, file_type: str) -> Dict[str, Any]:
        """提取文件元数据"""
        metadata = {
            'file_size': file_path.stat().st_size,
            'created_at': file_path.stat().st_ctime,
            'modified_at': file_path.stat().st_mtime
        }
        
        try:
            if file_type == 'image':
                metadata.update(self._extract_image_metadata(file_path))
            elif file_type == 'video':
                metadata.update(self._extract_video_metadata(file_path))
            elif file_type == 'audio':
                metadata.update(self._extract_audio_metadata(file_path))
            elif file_type == 'document':
                metadata.update(self._extract_document_metadata(file_path))
        except Exception as e:
            log.warning(f"Failed to extract metadata for {file_path}: {e}")
        
        return metadata
    
    def _extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取图片元数据"""
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
                
                # 提取EXIF数据
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        metadata['exif'] = {
                            'camera_make': exif.get(271),
                            'camera_model': exif.get(272),
                            'datetime': exif.get(306),
                            'gps_info': exif.get(34853)
                        }
                
                return metadata
        except Exception as e:
            log.error(f"Error extracting image metadata: {e}")
            return {}
    
    def _extract_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取视频元数据"""
        try:
            with VideoFileClip(str(file_path)) as clip:
                metadata = {
                    'duration': clip.duration,
                    'fps': clip.fps,
                    'width': clip.w,
                    'height': clip.h,
                    'aspect_ratio': round(clip.w / clip.h, 2) if clip.h > 0 else None
                }
                
                if clip.audio:
                    metadata['has_audio'] = True
                    metadata['audio_duration'] = clip.audio.duration
                else:
                    metadata['has_audio'] = False
                
                return metadata
        except Exception as e:
            log.error(f"Error extracting video metadata: {e}")
            return {}
    
    def _extract_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取音频元数据"""
        try:
            # 对于WAV文件
            if file_path.suffix.lower() == '.wav':
                with wave.open(str(file_path), 'rb') as wav:
                    metadata = {
                        'channels': wav.getnchannels(),
                        'sample_width': wav.getsampwidth(),
                        'frame_rate': wav.getframerate(),
                        'frames': wav.getnframes(),
                        'duration': wav.getnframes() / wav.getframerate()
                    }
                    return metadata
            
            # 对于其他音频格式，可以使用其他库
            return {'format': file_path.suffix.lower()}
            
        except Exception as e:
            log.error(f"Error extracting audio metadata: {e}")
            return {}
    
    def _extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """提取文档元数据"""
        try:
            metadata = {
                'format': file_path.suffix.lower(),
                'encoding': 'utf-8'  # 默认编码
            }
            
            # 对于文本文件，计算行数和字符数
            if file_path.suffix.lower() in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    metadata.update({
                        'lines': len(content.splitlines()),
                        'characters': len(content),
                        'words': len(content.split())
                    })
            
            return metadata
            
        except Exception as e:
            log.error(f"Error extracting document metadata: {e}")
            return {}
    
    def generate_thumbnail(self, file_path: Path, file_type: str) -> Optional[Path]:
        """生成缩略图"""
        try:
            thumbnail_name = f"{file_path.stem}_thumb.jpg"
            thumbnail_path = self.thumbnails_dir / thumbnail_name
            
            if file_type == 'image':
                return self._generate_image_thumbnail(file_path, thumbnail_path)
            elif file_type == 'video':
                return self._generate_video_thumbnail(file_path, thumbnail_path)
            elif file_type == 'document':
                return self._generate_document_thumbnail(file_path, thumbnail_path)
            elif file_type == 'audio':
                return self._generate_audio_thumbnail(file_path, thumbnail_path)
            else:
                return None
                
        except Exception as e:
            log.error(f"Error generating thumbnail for {file_path}: {e}")
            return None
    
    def _generate_image_thumbnail(self, file_path: Path, thumbnail_path: Path) -> Path:
        """生成图片缩略图"""
        with Image.open(file_path) as img:
            # 转换为RGB模式以确保JPEG兼容性
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 使用ImageOps.fit确保缩略图比例正确
            config = self.thumbnail_config['image']
            thumbnail = ImageOps.fit(img, config['size'], Image.Resampling.LANCZOS)
            
            thumbnail.save(thumbnail_path, 'JPEG', quality=config['quality'])
            return thumbnail_path
    
    def _generate_video_thumbnail(self, file_path: Path, thumbnail_path: Path) -> Path:
        """生成视频缩略图"""
        with VideoFileClip(str(file_path)) as clip:
            config = self.thumbnail_config['video']
            
            # 选择截取时间（第1秒或视频中间）
            time_to_capture = min(config['frame_time'], clip.duration / 2)
            
            # 截取帧
            frame = clip.get_frame(time_to_capture)
            
            # 转换为PIL Image
            img = Image.fromarray(frame)
            
            # 调整尺寸
            thumbnail = ImageOps.fit(img, config['size'], Image.Resampling.LANCZOS)
            
            thumbnail.save(thumbnail_path, 'JPEG', quality=85)
            return thumbnail_path
    
    def _generate_document_thumbnail(self, file_path: Path, thumbnail_path: Path) -> Optional[Path]:
        """生成文档缩略图（简单的文本预览）"""
        try:
            config = self.thumbnail_config['document']
            
            # 创建一个简单的文档图标缩略图
            img = Image.new('RGB', config['size'], color='white')
            
            # 这里可以添加更复杂的文档预览生成逻辑
            # 比如使用PIL绘制文档内容的前几行
            
            img.save(thumbnail_path, 'JPEG', quality=85)
            return thumbnail_path
            
        except Exception as e:
            log.error(f"Error generating document thumbnail: {e}")
            return None
    
    def _generate_audio_thumbnail(self, file_path: Path, thumbnail_path: Path) -> Optional[Path]:
        """生成音频缩略图（音频波形图或默认图标）"""
        try:
            config = self.thumbnail_config['audio']
            
            # 创建一个简单的音频图标
            img = Image.new('RGB', config['size'], color='lightblue')
            
            # 这里可以添加音频波形图生成逻辑
            
            img.save(thumbnail_path, 'JPEG', quality=85)
            return thumbnail_path
            
        except Exception as e:
            log.error(f"Error generating audio thumbnail: {e}")
            return None
    
    def analyze_content_for_tagging(self, file_path: Path, file_type: str, metadata: Dict[str, Any]) -> List[str]:
        """基于内容分析自动生成标签"""
        tags = []
        
        try:
            # 基于文件类型的基础标签
            tags.append(file_type)
            
            # 基于文件大小
            size = metadata.get('file_size', 0)
            if size > 100 * 1024 * 1024:  # 100MB+
                tags.append('大文件')
            elif size < 1024 * 1024:  # 1MB-
                tags.append('小文件')
            
            # 基于具体类型的分析
            if file_type == 'image':
                tags.extend(self._analyze_image_content(file_path, metadata))
            elif file_type == 'video':
                tags.extend(self._analyze_video_content(file_path, metadata))
            elif file_type == 'audio':
                tags.extend(self._analyze_audio_content(file_path, metadata))
            elif file_type == 'document':
                tags.extend(self._analyze_document_content(file_path, metadata))
            
            # 基于文件名分析
            filename_tags = self._analyze_filename(file_path.name)
            tags.extend(filename_tags)
            
        except Exception as e:
            log.error(f"Error analyzing content for tagging: {e}")
        
        # 去重并返回
        return list(set(tags))
    
    def _analyze_image_content(self, file_path: Path, metadata: Dict[str, Any]) -> List[str]:
        """分析图片内容"""
        tags = []
        
        # 基于尺寸
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        
        if width and height:
            if width > height:
                tags.append('横向')
            elif height > width:
                tags.append('纵向')
            else:
                tags.append('方形')
            
            # 分辨率等级
            pixels = width * height
            if pixels > 2000000:  # 2MP+
                tags.append('高分辨率')
            elif pixels < 500000:  # 0.5MP-
                tags.append('低分辨率')
        
        return tags
    
    def _analyze_video_content(self, file_path: Path, metadata: Dict[str, Any]) -> List[str]:
        """分析视频内容"""
        tags = []
        
        # 基于时长
        duration = metadata.get('duration', 0)
        if duration:
            if duration < 60:  # 1分钟以内
                tags.append('短视频')
            elif duration > 1800:  # 30分钟以上
                tags.append('长视频')
        
        # 基于分辨率
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        if width >= 1920 and height >= 1080:
            tags.append('高清')
        elif width >= 1280 and height >= 720:
            tags.append('标清')
        
        # 基于音频
        if metadata.get('has_audio'):
            tags.append('有声')
        else:
            tags.append('无声')
        
        return tags
    
    def _analyze_audio_content(self, file_path: Path, metadata: Dict[str, Any]) -> List[str]:
        """分析音频内容"""
        tags = []
        
        # 基于时长
        duration = metadata.get('duration', 0)
        if duration:
            if duration < 60:
                tags.append('短音频')
            elif duration > 1800:
                tags.append('长音频')
        
        return tags
    
    def _analyze_document_content(self, file_path: Path, metadata: Dict[str, Any]) -> List[str]:
        """分析文档内容"""
        tags = []
        
        format_type = metadata.get('format', '').lower()
        if format_type == '.pdf':
            tags.append('PDF文档')
        elif format_type in ['.doc', '.docx']:
            tags.append('Word文档')
        elif format_type == '.txt':
            tags.append('文本文件')
        elif format_type == '.md':
            tags.append('Markdown')
        
        return tags
    
    def _analyze_filename(self, filename: str) -> List[str]:
        """基于文件名分析标签"""
        tags = []
        
        # 转换为小写进行分析
        name_lower = filename.lower()
        
        # 常见关键词映射
        keyword_mapping = {
            'logo': '标志',
            'banner': '横幅',
            'avatar': '头像',
            'thumbnail': '缩略图',
            'icon': '图标',
            'background': '背景',
            'template': '模板',
            'draft': '草稿',
            'final': '最终版',
            'v1': '版本1',
            'v2': '版本2',
            'test': '测试',
            'demo': '演示',
            'sample': '样本',
            'preview': '预览'
        }
        
        for keyword, tag in keyword_mapping.items():
            if keyword in name_lower:
                tags.append(tag)
        
        return tags
    
    def process_file(
        self, 
        file_path: Path, 
        original_filename: str,
        generate_thumbnail: bool = True,
        auto_tag: bool = True
    ) -> Dict[str, Any]:
        """处理文件并返回完整信息"""
        
        # 确定文件类型
        file_type = self.get_file_type(original_filename)
        
        # 计算文件哈希
        file_hash = self.calculate_file_hash(file_path)
        
        # 获取MIME类型
        mime_type = self.get_file_mime_type(file_path)
        
        # 提取元数据
        metadata = self.extract_metadata(file_path, file_type)
        
        # 生成缩略图
        thumbnail_path = None
        if generate_thumbnail:
            thumbnail_path = self.generate_thumbnail(file_path, file_type)
        
        # 自动标签
        auto_tags = []
        if auto_tag:
            auto_tags = self.analyze_content_for_tagging(file_path, file_type, metadata)
        
        return {
            'file_path': str(file_path),
            'original_filename': original_filename,
            'file_type': file_type,
            'file_hash': file_hash,
            'mime_type': mime_type,
            'file_size': file_path.stat().st_size,
            'metadata': metadata,
            'thumbnail_path': str(thumbnail_path) if thumbnail_path else None,
            'auto_tags': auto_tags,
            'processing_time': time.time()
        }


# 全局文件处理器实例
_file_processor = None

def get_file_processor(upload_dir: str) -> HSAIFileProcessor:
    """获取文件处理器实例"""
    global _file_processor
    if _file_processor is None:
        _file_processor = HSAIFileProcessor(upload_dir)
    return _file_processor
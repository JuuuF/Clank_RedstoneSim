"""OpenGL drawing with PySide6's own GL wrappers (no PyOpenGL; doc/decisions.md ADR-002).

One shader draws three kinds of vertex streams: opaque triangles, translucent triangles
(drawn after, without depth writes) and lines (outlines, sections, grid). The world mesh is
split into chunks (``redsim.ui.geometry.ChunkedMesh``), each with its own buffers, so a change
re-uploads only the chunks it touched. Vertices are ``x, y, z, r, g, b, a`` float32.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QMatrix4x4, QOpenGLContext, QOpenGLFunctions
from PySide6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLVertexArrayObject,
)

GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_LINES = 0x0001
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_FALSE = 0
GL_TRUE = 1
GL_POLYGON_OFFSET_FILL = 0x8037
GL_SCISSOR_TEST = 0x0C11
GL_STENCIL_TEST = 0x0B90
GL_CULL_FACE = 0x0B44

VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec4 color;
uniform mat4 mvp;
out vec4 vColor;
void main() { gl_Position = mvp * vec4(position, 1.0); vColor = color; }
"""
FRAGMENT_SHADER = """#version 330 core
in vec4 vColor;
out vec4 fragColor;
void main() { fragColor = vColor; }
"""


class _Stream:
    def __init__(self) -> None:
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self.vbo.create()
        self.count = 0

    def upload(self, program: QOpenGLShaderProgram, data: np.ndarray) -> None:
        data = np.ascontiguousarray(data, dtype=np.float32)
        self.count = len(data)
        self.vao.bind()
        self.vbo.bind()
        self.vbo.allocate(data.tobytes(), data.nbytes)
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, 28)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 12, 4, 28)
        self.vao.release()

    def destroy(self) -> None:
        self.vbo.destroy()
        self.vao.destroy()


class Renderer:
    """Owns GL resources; must be created and used with the widget's context current."""

    def __init__(self) -> None:
        context = QOpenGLContext.currentContext()
        assert context is not None, "a current OpenGL context is required"
        self.gl: QOpenGLFunctions = context.functions()
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER)
        if not self.program.link():
            raise RuntimeError(self.program.log())
        self.program.bind()
        #: Chunk key → (opaque, translucent) streams.
        self.chunks: dict[object, tuple[_Stream, _Stream]] = {}
        self.lines = _Stream()

    def set_chunk(self, key: object, opaque: np.ndarray, translucent: np.ndarray) -> None:
        streams = self.chunks.get(key)
        if streams is None:
            streams = self.chunks[key] = (_Stream(), _Stream())
        self.program.bind()
        streams[0].upload(self.program, opaque)
        streams[1].upload(self.program, translucent)

    def remove_chunk(self, key: object) -> None:
        streams = self.chunks.pop(key, None)
        if streams is not None:
            for stream in streams:
                stream.destroy()

    def upload_lines(self, lines: np.ndarray) -> None:
        self.program.bind()
        self.lines.upload(self.program, lines)

    def draw(self, mvp: np.ndarray, width: int, height: int, background: tuple[float, ...]) -> None:
        gl = self.gl
        # A QPainter overlay drawn after us may leave any of these changed.
        gl.glDisable(GL_SCISSOR_TEST)
        gl.glDisable(GL_STENCIL_TEST)
        gl.glDisable(GL_CULL_FACE)
        gl.glDisable(GL_BLEND)
        gl.glDepthMask(GL_TRUE)
        gl.glViewport(0, 0, width, height)
        gl.glClearColor(*background)
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        gl.glEnable(GL_DEPTH_TEST)
        self.program.bind()
        location = self.program.uniformLocation("mvp")
        self.program.setUniformValue(location, QMatrix4x4(*mvp.astype(np.float32).flatten()))
        for opaque, _ in self.chunks.values():
            if opaque.count:
                opaque.vao.bind()
                gl.glDrawArrays(GL_TRIANGLES, 0, opaque.count)
        if self.lines.count:
            self.lines.vao.bind()
            gl.glDrawArrays(GL_LINES, 0, self.lines.count)
        translucent = [stream for _, stream in self.chunks.values() if stream.count]
        if translucent:
            gl.glEnable(GL_BLEND)
            gl.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            gl.glDepthMask(GL_FALSE)
            for stream in translucent:
                stream.vao.bind()
                gl.glDrawArrays(GL_TRIANGLES, 0, stream.count)
            gl.glDepthMask(GL_TRUE)
            gl.glDisable(GL_BLEND)
        self.lines.vao.release()

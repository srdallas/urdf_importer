#!/usr/bin/python3

import os
from shutil import copy
from typing import Dict, List, Tuple, Union
from xml.etree import ElementTree

import bpy
import rospkg
from bpy.types import (Armature, BlendData, Bone, Camera, Image, Light,
                       Material, MaterialSlot, Mesh, Object)
from math import pi
from mathutils import Euler, Vector, Matrix
from urdf_parser_py.urdf import URDF, Joint, Link, Visual

TMP_FOLDER_PATH = 'texture/'
TMP_TEXTURE_PATH = TMP_FOLDER_PATH
TMP_FILE_PATH = 'tmp.dae'


def urdf_cleanup(file_path: str) -> str:
    tree = ElementTree.parse(file_path)
    root = tree.getroot()

    newroot = ElementTree.Element(root.tag)
    newroot.set('name', root.get('name'))

    for element in root:
        if element.tag == 'link' or element.tag == 'joint' or element.tag == 'material':
            newroot.append(element)

    return ElementTree.tostring(newroot)


def fix_up_axis_and_get_materials(file_path: str):
    tree = ElementTree.parse(file_path)
    root = tree.getroot()

    tmp_file_path = file_path
    dir_path = os.path.dirname(file_path)
    mat_sampler2D_dict: Dict[str, Dict[str, str]] = {}

    mat_dict: Dict[str, str] = {}
    effect_dict: Dict[str, List[str]] = {}
    sampler2D_dict: Dict[str, str] = {}
    surface_dict: Dict[str, str] = {}
    image_dict: Dict[str, str] = {}
    if not os.path.exists(TMP_TEXTURE_PATH):
        os.makedirs(TMP_TEXTURE_PATH)

    for ele1 in root:
        if 'asset' in ele1.tag:
            for ele2 in ele1:
                if 'up_axis' in ele2.tag:
                    ele2.text = 'Z_UP'
                    tmp_file_path = TMP_FILE_PATH

        if 'library_materials' in ele1.tag:
            for ele2 in ele1:
                if 'material' in ele2.tag:
                    mat_name = ele2.attrib['name']
                    for ele3 in ele2:
                        if 'instance_effect' in ele3.tag:
                            effect_id = ele3.attrib['url']
                            if effect_id.startswith('#'):
                                effect_id = effect_id[1:]
                            mat_dict[mat_name] = effect_id

        if 'library_effects' in ele1.tag:
            for ele2 in ele1:
                if 'effect' in ele2.tag:
                    effect_id = ele2.attrib['id']
                    effect_dict[effect_id] = []
                    for ele3 in ele2:
                        if 'profile_COMMON' in ele3.tag:
                            for ele4 in ele3:
                                if 'newparam' in ele4.tag:
                                    param_name = ele4.attrib['sid']
                                    for ele5 in ele4:
                                        if 'surface' in ele5.tag:
                                            for ele6 in ele5:
                                                if 'init_from' in ele6.tag:
                                                    surface_dict[param_name] = ele6.text
                                        if 'sampler2D' in ele5.tag:
                                            for ele6 in ele5:
                                                if 'source' in ele6.tag:
                                                    effect_dict[effect_id].append(
                                                        param_name)
                                                    sampler2D_dict[param_name] = ele6.text

        if 'library_images' in ele1.tag:
            for ele2 in ele1:
                if 'image' in ele2.tag:
                    image_name = ele2.attrib['name']
                    for ele3 in ele2:
                        if 'init_from' in ele3.tag:
                            tmp_file_path = TMP_FILE_PATH
                            file_name, file_ext = os.path.splitext(ele3.text)
                            file_hash = str(abs(hash(file_path)) % (10 ** 3))
                            file = 'T_' + file_name + '_' + file_hash + file_ext
                            copy(dir_path + '/' + ele3.text,
                                 TMP_TEXTURE_PATH + file)
                            ele3.text = TMP_TEXTURE_PATH + file
                            image_dict[image_name] = ele3.text

    for mat_name in mat_dict:
        mat_sampler2D_dict[mat_name] = {}
        effect_id = mat_dict[mat_name]
        for effect_name in effect_dict[effect_id]:
            sampler2D_name = sampler2D_dict.get(effect_name)
            image_name = surface_dict.get(sampler2D_name)
            image_path = image_dict.get(image_name)
            mat_sampler2D_dict[mat_name][effect_name] = image_path

    if tmp_file_path == TMP_FILE_PATH:
        tree.write(tmp_file_path)

    return (tmp_file_path, mat_sampler2D_dict)


def clean_up() -> None:
    if os.path.exists(TMP_FILE_PATH):
        os.remove(TMP_FILE_PATH)
    return None


def clear_data(data: BlendData) -> None:
    armature: Armature
    for armature in data.armatures:
        data.armatures.remove(armature)
    mesh: Mesh
    for mesh in data.meshes:
        data.meshes.remove(mesh)
    object: Object
    for object in data.objects:
        data.objects.remove(object)
    material: Material
    for material in data.materials:
        data.materials.remove(material)
    camera: Camera
    for camera in data.cameras:
        data.cameras.remove(camera)
    light: Light
    for light in data.lights:
        data.lights.remove(light)
    image: Image
    for image in data.images:
        data.images.remove(image)

    return None


def remove_identical_materials() -> None:
    mat_uniques: List[Material] = []
    object: Object
    for object in bpy.data.objects:

        for material_slot in object.material_slots:
            mat = material_slot.material
            if not hasattr(mat.node_tree, 'nodes'):
                continue
            mat_base_color = mat.node_tree.nodes['Principled BSDF'].inputs.get(
                'Base Color')
            is_mat_not_from_file = not mat_base_color.links
            mat_unique: Material
            for mat_unique in mat_uniques:
                if not hasattr(mat_unique.node_tree, 'nodes'):
                    break
                mat_unique_base_color = mat_unique.node_tree.nodes['Principled BSDF'].inputs.get(
                    'Base Color')
                if is_mat_not_from_file:
                    if [i for i in mat_base_color.default_value] == [i for i in mat_unique_base_color.default_value]:
                        object.material_slots[mat.name].material = mat_unique
                        break
                else:
                    if mat_base_color.links[0].from_node.image.name == mat_unique_base_color.links[0].from_node.image.name:
                        object.material_slots[mat.name].material = mat_unique
                        break
            if mat not in mat_uniques:
                mat_uniques.append(mat)
            else:
                bpy.data.materials.remove(mat)

        object.select_set(False)
    return None


def fix_alpha() -> None:
    for mat in bpy.data.materials:
        if hasattr(mat.node_tree, 'nodes'):
            mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 1.0


def rename_materials(base_name: str) -> None:
    for object in bpy.data.objects:
        for material_slot in object.material_slots:
            material_slot.material.name = 'M_' + base_name
    return None


class RobotBuilder:
    def __init__(self, file_path: str):
        xml_string = urdf_cleanup(file_path)
        self.robot: URDF = URDF.from_xml_string(xml_string)
        self.link_pose: Dict[str, Tuple[Vector, Euler]] = {}
        self.arm_bones: Dict[str, Bone] = {}
        self.root: Object = None
        self.root_name = 'root'
        self.bone_tail = '.bone'
        self.parent_links = None
        self.build_robot(file_path)
        clean_up()

    def build_robot(self, file_path) -> None:
        clear_data(bpy.data)
        self.create_materials()
        self.konfigure_mesh_path()
        self.add_root_armature()
        self.build_root()
        self.build_chain()
        fix_alpha()
        remove_identical_materials()
        robot_name = os.path.basename(os.path.splitext(file_path)[0])
        rename_materials(robot_name)
        return None

    def create_materials(self) -> None:
        for material in self.robot.materials:

            if material.color is not None and hasattr(material.color, 'rgba'):
                if bpy.data.materials.get(material.name):
                    print('Material', material.name, 'already exists')
                else:
                    mat: Material = bpy.data.materials.new(name=material.name)
                    mat.diffuse_color = material.color.rgba
        return None

    def konfigure_mesh_path(self) -> None:
        link: Link
        for link in self.robot.links:
            visual: Visual
            for visual in link.visuals:
                if hasattr(visual.geometry, 'filename'):
                    rel_path: str = visual.geometry.filename
                    while os.path.dirname(rel_path) != 'package:':
                        rel_path = os.path.dirname(rel_path)
                    pkg_name = os.path.basename(rel_path)
                    pkg_path = rospkg.RosPack().get_path(pkg_name)
                    abs_path = os.path.dirname(
                        pkg_path) + visual.geometry.filename.replace('package://', '/')
                    if os.path.exists(abs_path):
                        visual.geometry.filename = abs_path
        return None

    def add_root_armature(self) -> None:
        arm: Armature = bpy.data.armatures.new('armatures')
        self.arm_bones = arm.bones
        self.root = bpy.data.objects.new(self.root_name, arm)
        self.root.show_in_front = True
        bpy.context.scene.collection.objects.link(self.root)
        return None

    def add_mesh(self, mesh_name: str, material: Material = None, file_path: Union[str, List[str]] = '', location=Vector(), rotation=Euler(), scale=Vector((1, 1, 1)), link_pos=Vector(), link_rot=Euler()) -> None:
        if isinstance(file_path, list):
            if file_path[0] == 'cylinder':
                bpy.ops.mesh.primitive_cylinder_add(
                    depth=file_path[1], radius=file_path[2], scale=(1, 1, 1))
            elif file_path[0] == 'cube':
                bpy.ops.mesh.primitive_cube_add(
                    size=1, scale=file_path[1])
            elif file_path[0] == 'sphere':
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=file_path[1], scale=(1, 1, 1))
            else:
                print('Object type', file_path[0], 'is not supported')
                return None
            object = bpy.context.object
            if material is None:
                material = bpy.data.materials.get('Material')
                if material is None:
                    material = bpy.data.materials.new(name='Material')

            object.data.materials.append(material)

        elif file_path:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.dae':
                (file_path, _) = fix_up_axis_and_get_materials(file_path)
                bpy.ops.wm.collada_import(filepath=file_path)
            elif file_ext == '.stl':
                bpy.ops.import_mesh.stl(filepath=file_path)
            else:
                print('File extension', file_ext, 'of',
                      file_path, 'is not supported')
                return None
            camera: Camera
            for camera in bpy.data.cameras:
                bpy.data.cameras.remove(camera)
            light: Light
            for light in bpy.data.lights:
                bpy.data.lights.remove(light)
            bpy.ops.object.join()
            if not bpy.context.object.data.uv_layers:
                bpy.ops.mesh.uv_texture_add()
            object = bpy.context.object
            if material is not None:
                object.data.materials.append(material)

        else:
            mesh = bpy.data.meshes.new(mesh_name)
            mesh.uv_layers.new()
            object = bpy.data.objects.new(mesh_name, mesh)
            bpy.context.scene.collection.objects.link(object)

        object.name = mesh_name
        object.rotation_mode = 'XYZ'
        object.rotation_euler.rotate(rotation)
        object.location.rotate(rotation)
        object.location += location
        object.scale *= scale

        # Change origin of mesh to link_pos and link_rot
        bpy.context.scene.cursor.location = link_pos
        bpy.context.scene.cursor.rotation_euler = link_rot
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.context.scene.cursor.location = Vector()
        bpy.context.scene.cursor.rotation_euler = Euler()
        return None

    def set_link_origin(self, link: Link) -> None:
        if hasattr(link, 'origin') and link.origin is not None:
            self.link_pose[link.name][0] += Vector(link.origin.xyz)
            self.link_pose[link.name][1].rotate(Euler(link.origin.rpy))
        return None

    def add_root_bone(self, link_name: str, bone_name: str) -> None:
        bpy.context.view_layer.objects.active = self.root
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        head = self.link_pose[link_name][0]
        tail = Vector((0.0, 0.1, 0.0))
        tail.rotate(self.link_pose[link_name][1])
        tail += head
        bone: Bone = self.root.data.edit_bones.new(bone_name)
        bone.head = head
        bone.tail = tail
        bpy.ops.object.mode_set(mode='OBJECT')
        return None

    def add_link_origin(self, pos: Vector, rot: Euler, tag: Union[Link, Joint, Visual]) -> Tuple[Vector, Euler]:
        if hasattr(tag, 'origin') and tag.origin is not None:
            pos_out = Vector(tag.origin.xyz)
            pos_out.rotate(rot)
            pos_out += pos
            rot_out = Euler(tag.origin.rpy)
            rot_out.rotate(rot)
            return (pos_out, rot_out)
        else:
            return (pos, rot)

    def get_link_data(self, link_pos: Vector, link_rot: Euler, link: Link, visual: Visual):
        visual_pos, visual_rot = self.add_link_origin(
            link_pos, link_rot, visual)

        if hasattr(visual.geometry, 'filename') and visual.geometry.filename:
            file_path = visual.geometry.filename
            mesh_name: str = link.name + '.' + os.path.basename(file_path)
            if len(mesh_name) > 63:
                print('Mesh', mesh_name,
                      'has more than 63 characters, the characters from 64 will be ignored')
                mesh_name = mesh_name[0:63]
        else:
            if hasattr(visual.geometry, 'length') and hasattr(visual.geometry, 'radius'):
                file_path = [
                    'cylinder', visual.geometry.length, visual.geometry.radius]
                mesh_name = link.name + '.cylinder'
            elif hasattr(visual.geometry, 'size'):
                file_path = [
                    'cube', visual.geometry.size]
                mesh_name = link.name + '.cube'
            elif hasattr(visual.geometry, 'radius'):
                file_path = [
                    'sphere', visual.geometry.radius]
                mesh_name = link.name + '.sphere'
            else:
                file_path = ''
                mesh_name = link.name + '.empty'

        if hasattr(visual.geometry, 'scale') and visual.geometry.scale:
            scale = Vector(visual.geometry.scale)
        else:
            scale = Vector((1, 1, 1))

        if hasattr(visual, 'material') and hasattr(visual.material, 'name'):
            material = bpy.data.materials.get(visual.material.name)
            if material is None:
                material = bpy.data.materials.new(visual.material.name)
        else:
            material = None

        return (mesh_name, file_path, visual_pos, visual_rot, scale, material)

    def bind_mesh_to_bone(self, mesh_name: str, bone_name: str) -> None:
        bpy.ops.object.mode_set(mode='POSE')

        object = bpy.context.scene.objects.get(mesh_name)
        object.select_set(True)
        self.arm_bones.active = self.arm_bones[bone_name]
        self.arm_bones[bone_name].select = True
        bpy.ops.object.parent_set(type='BONE')
        object.select_set(False)
        self.arm_bones[bone_name].select = False

        bpy.ops.object.mode_set(mode='OBJECT')
        return None

    def add_bone(self, link: Link, joint: Joint, joint_pos: Vector, joint_rot: Euler, bone_name: str) -> None:
        bpy.context.view_layer.objects.active = self.root
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        head = joint_pos
        tail = Vector((0.0, 0.0, 0.1))

        if hasattr(joint, 'axis') and joint.axis is not None and Vector(joint.axis).magnitude != 0:
            tail = Vector(joint.axis).normalized() * 0.1

        tail.rotate(joint_rot)

        bone: Bone = self.root.data.edit_bones.new(bone_name)
        bone.head = head
        bone.tail = head + tail

        if self.robot.parent_map[link.name][1] == self.robot.get_root():
            bone.parent = self.root.data.edit_bones['root' + self.bone_tail]
        else:
            parent_joint = self.robot.parent_map[self.robot.parent_map[link.name][1]][0]
            parent_joint_name = parent_joint + '.' + \
                str(self.robot.joint_map[parent_joint].type) + self.bone_tail
            bone.parent = self.root.data.edit_bones[parent_joint_name]

        bpy.ops.object.mode_set(mode='OBJECT')
        return None

    def add_root_mesh_and_bone(self, mesh_name: str, material: Material, file_path: Union[str, List[str]], link: Link, pos: Vector, rot: Euler, scale: Vector = Vector((1, 1, 1))) -> None:
        self.add_mesh(mesh_name, material, file_path, pos, rot, scale,
                      self.link_pose[link.name][0], self.link_pose[link.name][1])
        bone_name = self.root_name + self.bone_tail
        self.add_root_bone(link.name, bone_name)
        self.bind_mesh_to_bone(
            mesh_name, bone_name)
        return None

    def add_mesh_and_bone(self, mesh_name: str, material: Material, file_path: Union[str, List[str]], link: Link, joint: Joint, visual_pos: Vector, visual_rot: Euler, joint_pos: Vector, joint_rot: Euler, scale=Vector((1, 1, 1))) -> None:
        self.add_mesh(mesh_name, material, file_path, visual_pos, visual_rot, scale,
                      self.link_pose[link.name][0], self.link_pose[link.name][1])
        bone_name = joint.name + '.' + str(joint.type) + self.bone_tail
        self.add_bone(link, joint, joint_pos, joint_rot, bone_name)
        self.bind_mesh_to_bone(mesh_name, bone_name)
        return None

    def build_root(self) -> None:
        root_link: Link = self.robot.link_map[self.robot.get_root()]
        self.link_pose[root_link.name] = (Vector(), Euler())
        self.set_link_origin(root_link)

        if root_link.visuals:
            visual: Visual
            for visual in root_link.visuals:
                mesh_name, file_path, visual_pos, visual_rot, scale, material = self.get_link_data(
                    self.link_pose[root_link.name][0], self.link_pose[root_link.name][1], root_link, visual)

                pos_tmp = self.link_pose[root_link.name][0].copy()
                pos_tmp.rotate(self.link_pose[root_link.name][1])
                visual_pos += pos_tmp

                rot_tmp = self.link_pose[root_link.name][1].copy()
                rot_tmp.rotate(visual_rot)
                visual_rot = rot_tmp

                self.add_root_mesh_and_bone(
                    mesh_name, material, file_path, root_link, visual_pos, visual_rot, scale)

        else:
            self.add_root_mesh_and_bone(
                root_link.name + '.empty', None, None, root_link, self.link_pose[root_link.name][0], self.link_pose[root_link.name][1])

        self.parent_links = [root_link]
        return None

    def build_chain(self) -> None:
        while(self.robot.child_map):

            # Make new parent links
            links = self.parent_links

            # Iterate through all parent links
            for link in links:
                self.set_link_origin(link)

                # Iterate through all children of parent link
                if self.robot.child_map.get(link.name):
                    for child_map in self.robot.child_map[link.name]:
                        child_pos = self.link_pose[link.name][0].copy()
                        child_rot = self.link_pose[link.name][1].copy()

                        child_joint = self.robot.joint_map[child_map[0]]
                        child_pos, child_rot = self.add_link_origin(
                            child_pos, child_rot, child_joint)
                        joint_pos = child_pos.copy()
                        joint_rot = child_rot.copy()

                        child_link = self.robot.link_map[child_map[1]]
                        child_pos, child_rot = self.add_link_origin(
                            child_pos, child_rot, child_link)

                        self.link_pose[child_link.name] = (
                            child_pos, child_rot)

                        if child_link.visuals:
                            visual: Visual
                            for visual in child_link.visuals:
                                mesh_name, file_path, visual_pos, visual_rot, scale, material = self.get_link_data(
                                    child_pos, child_rot, child_link, visual)
                                self.add_mesh_and_bone(
                                    mesh_name, material, file_path, child_link, child_joint, visual_pos, visual_rot, joint_pos, joint_rot, scale)

                        else:
                            self.add_mesh_and_bone(
                                child_link.name + '.empty', None, None, child_link, child_joint, child_pos, child_rot, joint_pos, joint_rot)

                        self.parent_links.append(child_link)

                    del self.robot.child_map[link.name]

                # Remove finish link from parent links
                self.parent_links.remove(link)
        return None

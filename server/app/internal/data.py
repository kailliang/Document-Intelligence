DOCUMENT_1 = """
<DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>METHOD AND SYSTEM FOR IDENTIFYING FINGERPRINT</title>
    </head>
    <body>
      <h1>Claims</h1>
      <p>
        1. A method for identifying fingerprint, characterized by comprising: 
        S1: adjusting a camera to focus the camera on a lens; S2: capturing 
        continuously by the camera fingerprint images formed by a finger 
        pressing the lens, and sending the fingerprint images to an image 
        processing module; and S3: processing the fingerprint images by the 
        image processing module so as to acquire the fingerprint.
      </p>
      <p>
        2. The method for identifying a fingerprint according to claim 1, 
        wherein, before step S3, the method further comprises: S31: adhering 
        an anti-fingerprint film on the outside of the lens.
      </p>
      <p>
        3. The method for identifying a fingerprint according to claim 1, 
        wherein, before step S2, the method further comprises: S21: setting 
        the camera to be in a continuous previewing state; and S22: connecting 
        the camera to the image processing module via a CSI interface.
      </p>
      <p>
        4. The method for identifying a fingerprint according to claim 1, 
        wherein, step S2 specifically comprises: S20: determining by the camera 
        whether a brightness component value Y is smaller than a preset value, 
        according to the YUV format; executing S23 of capturing a fingerprint 
        image by the camera and sending the fingerprint image to the image 
        processing module, if the brightness component value Y is smaller than 
        the preset value; otherwise, executing S24 of capturing continuously 
        by the camera fingerprint images formed by the finger pressing the 
        lens, and returning to the execution of S20.
      </p>
      <p>
        5. The method for identifying a fingerprint according to claim 1, 
        wherein, step S3 specifically comprises: S32: converting the fingerprint 
        image into a black-and-white gray-scale image by the image processing 
        module and performing binarization on the black-and-white gray-scale 
        image so as to obtain a black-and-white texture image; S33: extracting 
        feature values of the black-and-white texture image and sending the 
        feature values to a system backstage for comparison; S34: acquiring a 
        fingerprint according to the comparison result.
      </p>
      <p>
        6. A system for identifying fingerprint, comprising a camera, a lens 
        and an image processing module, the system performing the following 
        steps: S1: adjusting the camera to focus the camera on the lens; S2: 
        capturing continuously by the camera fingerprint images formed by a 
        finger pressing the lens, and sending the fingerprint images to the 
        image processing module; and S3: processing the fingerprint images by 
        the image processing module so as to acquire the fingerprint.
      </p>
      <p>
        7. The system for identifying fingerprint according to claim 6, wherein, 
        before step S3, the following step is further included: S31: adhering 
        an anti-fingerprint film on the outside of the lens.
      </p>
      <p>
        8. The system for identifying fingerprint according to claim 6, wherein, 
        before step S2, the following step is further included: S21: setting 
        the camera to be in a continuous previewing state; and S22: connecting 
        the camera to the image processing module via a CSI interface.
      </p>
      <p>
        9. The system for identifying fingerprint according to claim 6, wherein, 
        step S2 specifically comprises: S20: determining by the camera whether 
        a brightness component value Y is smaller than a preset value, according 
        to the YUV format; executing S23 of capturing a fingerprint image by 
        the camera and sending the fingerprint image to the image processing 
        module, if the brightness component value Y is smaller than the preset 
        value; otherwise, executing S24 of capturing continuously by the camera 
        fingerprint images formed by the finger pressing the lens, and returning 
        to the execution of S20.
      </p>
      <p>
        10. The system for identifying fingerprint according to claim 6, wherein, 
        step S3 specifically comprises: S32: converting the fingerprint image 
        into a black-and-white gray-scale image by the image processing module 
        and performing binarization on the black-and-white gray-scale image so 
        as to obtain a black-and-white texture image; S33: extracting feature 
        values of the black-and-white texture image and sending the feature 
        values to a system backstage for comparison; S34: acquiring a fingerprint 
        according to the comparison result.
      </p>
    </body>
  </html>
"""

DOCUMENT_2 = """
<DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>THREE-SPEED MOTORCYCLE TRANSMISSION</title>
    </head>
    <body>
      <h1>Claims</h1>
      <p>
        1. A three-speed motorcycle transmission (1) used as a transmission 
        device for transmitting motion generated by an engine to a drive wheel 
        on a motorcycle, the transmission (1) comprising: a crankshaft (2) 
        receiving the motion of the engine, on which a first pulley (9) is 
        mounted; a main shaft (3) on which a second pulley (12) and a first 
        group of three gears (21, 22, 23) are mounted, a transmission belt (11) 
        connecting the first pulley and the second pulley (9, 12); a countershaft 
        (4) connected to the drive wheel, comprising a second group of three 
        gears (31, 32, 33), the second group of three gears meshing in pairs 
        with corresponding gears (21, 22, 23) of the first group of three gears 
        for transmitting a first, second and third speed; a clutch (10) 
        selectively acting on at least two pairs of gears assigned to the second 
        and third speed transmissions; and two free wheels (15, 18) provided on 
        the gear pairs for the first and second speed transmissions, respectively.
      </p>
      <p>
        2. The three-speed transmission (1) according to claim 1, wherein the 
        free wheels (15, 18) are mounted on the main shaft (3).
      </p>
      <p>
        3. The three-speed transmission (1) according to claim 1, wherein the 
        drive belt (11) is a synchronous toothed belt and the pulleys (9, 12) 
        are provided with teeth to achieve synchronous transmission of motion.
      </p>
      <p>
        4. The three-speed transmission (1) according to claim 1, wherein the 
        crankshaft (2) comprises a centrifugal clutch (8).
      </p>
      <p>
        5. The three-speed transmission (1) according to claim 1, wherein the 
        secondary shaft (4) is engaged with a hub shaft, which is connected 
        directly to a driving wheel, by means of a pair of gears determining 
        a reducing ratio.
      </p>
      <p>
        6. The three-speed transmission (1) according to claim 1, wherein said 
        selective clutch (10) is arranged on the primary shaft (3).
      </p>
      <p>
        7. The three-speed transmission (1) according to claim 6, wherein said 
        selective clutch (10) is positioned between a second and a third driving 
        gear (22, 23) of said pair of driving wheels, assigned to the transmission 
        of the second and third speeds, and wherein the third driving gear (23) 
        is positioned between the other two driving gears (21, 22), assigned to 
        the transmission of the first and second speed.
      </p>
      <p>
        8. The three-speed transmission (1) according to claim 7, wherein the 
        third driving gear (23) is arranged between the first driving gear (21), 
        assigned to the transmission of the first speed, and the clutch (10), 
        and analogously the third driven gear (33) arranged between the first 
        driven gear (31) and the clutch (10).
      </p>
      <p>
        9. The three-speed transmission (1) according to claim 1, wherein said 
        selective clutch (10) comprises a double synchronizer, each synchronizer 
        comprising a synchronization plate (16, 17), which is activated by 
        synchronizing means of centrifugal type, respectively associated to the 
        pairs of gears assigned to the transmission of the second and third speeds.
      </p>
      <p>
        10. Motorcycle or scooter vehicle including a three speed transmission 
        of claim 1.
      </p>
    </body>
  </html>
"""

DOCUMENT_3 = """
<DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>ENGINE</title>
    </head>
    <body>
      <h1>Claims</h1>
      <p>
        1. An engine comprising a compressor and a closed fluid circuit connected to an input and an output of the compressor so that compressed gas can be driven through the circuit by the compressor, 
        the output of the compressor being connected through the fluid circuit to a turbine assembly, 
        the turbine assembly comprising at least one set of turbine blades connected to a rotating shaft which, 
        in use, serves as the output of the engine; 
        a condenser for receiving fluid in the circuit flowing through the turbine assembly and reducing the temperature and pressure of the compressed gas, 
        the outlet of the condenser being connected to the inlet of the compressor.
      </p>
      <p>
        2. An engine according to claim 1 further comprising a check valve 
        positioned between the outlet of the condenser and the input of 
        the compressor and configured to allow gas to flow only in the 
        direction from the condenser to the compressor.
      </p>
      <p>
        3. An engine according to claim 1 wherein the turbine component 
        comprises plural sets of turbine blades, each attached to the 
        rotating shaft.
      </p>
      <p>
        4. An engine according to claim 1 wherein the compressed gas is 
        one of carbon dioxide or ammonia.
      </p>
      <p>
        5. An engine according to claim 1 further comprising a generator 
        connected to an output shaft.
      </p>
      <p>
        6. An engine according to claim 5 wherein at least some of the 
        electricity generated by the generator is employed to power 
        the compressor.
      </p>
      <p>
        7. An engine according to claim 1 further comprising energy 
        recovery means associated with the condenser to recover a heat 
        energy therefrom and provide an additional energy output from 
        the engine.
      </p>
    </body>
  </html>
"""
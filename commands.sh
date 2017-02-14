nohup  ./plan.py blind 'run_hanoi4     ( "samples/hanoi4_fc2"               ,"fc2", import_module("puzzles.hanoi")             )'   &> blind-hanoi4     &
nohup  ./plan.py blind 'run_hanoi10     ( "samples/hanoi10_fc2"               ,"fc2", import_module("puzzles.hanoi")             )'   &> blind-hanoi10     &
nohup  ./plan.py blind 'run_puzzle    ( "samples/mnist_puzzle33p_fc2"     ,"fc2", import_module("puzzles.mnist_puzzle")      )'   &> blind-mnist     &
nohup  ./plan.py blind 'run_puzzle    ( "samples/lenna_puzzle33p_fc2"     ,"fc2", import_module("puzzles.lenna_puzzle")      )'   &> blind-lenna     &
nohup  ./plan.py blind 'run_puzzle    ( "samples/mandrill_puzzle33p_fc2"  ,"fc2", import_module("puzzles.mandrill_puzzle")   )'   &> blind-mandrill  &
nohup  ./plan.py blind 'run_lightsout ( "samples/digital_lightsout_fc2"   ,"fc2", import_module("puzzles.digital_lightsout") )'   &> blind-lightsout &
nohup  ./plan.py pdb   'run_hanoi4     ( "samples/hanoi4_fc2"               ,"fc2", import_module("puzzles.hanoi")             )'   &> pdb-hanoi4     &
nohup  ./plan.py pdb   'run_hanoi10     ( "samples/hanoi10_fc2"               ,"fc2", import_module("puzzles.hanoi")             )'   &> pdb-hanoi10     &
nohup  ./plan.py pdb   'run_puzzle    ( "samples/mnist_puzzle33p_fc2"     ,"fc2", import_module("puzzles.mnist_puzzle")      )'   &> pdb-mnist     &
nohup  ./plan.py pdb   'run_puzzle    ( "samples/lenna_puzzle33p_fc2"     ,"fc2", import_module("puzzles.lenna_puzzle")      )'   &> pdb-lenna     &
nohup  ./plan.py pdb   'run_puzzle    ( "samples/mandrill_puzzle33p_fc2"  ,"fc2", import_module("puzzles.mandrill_puzzle")   )'   &> pdb-mandrill  &
nohup  ./plan.py pdb   'run_lightsout ( "samples/digital_lightsout_fc2"   ,"fc2", import_module("puzzles.digital_lightsout") )'   &> pdb-lightsout &

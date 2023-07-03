def reduce_set_of_guards(sog):
    if not sog:
        return {}

    # first, resolve all generalizations
    new_sog = set()
    for g in sog:
        new_sog = new_sog.union(resolve_all_x(g))
    changed = True
    # blow up the set of guards with all possible generalizations
    while changed:
        blown_up_sog = set(new_sog)
        for guard in new_sog:  # for each guard
            for i, o in enumerate(guard):  # for each bit in the guard
                # construct hypothetical test_guard
                test_guard = flip_guard_bit(guard, i)

                # check if the test_guard and the guard are different (they are not if 'X' got "flipped")
                if test_guard == guard:
                    continue

                # if the hypothetical guard is not also in the new sog, we cannot reduce
                test_guard_in_new_sog = False
                for g in new_sog:
                    if compare_obs(test_guard, g):
                        test_guard_in_new_sog = True
                if not test_guard_in_new_sog:
                    continue

                # create a reduced guard
                reduced_guard = replace_guard_bit(guard, i, 'X')
                # add it to the reduced sog
                blown_up_sog.add(reduced_guard)

        if new_sog == blown_up_sog:
            changed = False

        new_sog = blown_up_sog

    # sog is all blown up with all possible generalizations
    unnecessary_guards = set()
    for guard in new_sog:
        for other_guard in new_sog:
            # skip yourself
            if guard == other_guard:
                continue

            # check if the guard subsumes the other_guard
            subsumes = True
            for j in range(len(guard)):
                if guard[j] == 'X':
                    continue
                if other_guard[j] == 'X':
                    subsumes = False
                if not guard[j] == other_guard[j]:
                    subsumes = False
            if subsumes:
                unnecessary_guards.add(other_guard)

    return new_sog.difference(unnecessary_guards)


def resolve_all_x(guard):
    return_set = set()
    for i, o in enumerate(guard):
        if o == 'X':
            return_set = return_set.union(resolve_all_x(replace_guard_bit(guard, i, '0')))
            return_set = return_set.union(resolve_all_x(replace_guard_bit(guard, i, '1')))

    if len(return_set) == 0:
        return_set.add(guard)
    return return_set

def flip_guard_bit(guard, bit, skip_ones=False):
    # construct hypothetical test_guard
    test_guard = list(guard)
    if guard[bit] == '1':
        if skip_ones:
            test_guard[bit] = '1'
        else:
            test_guard[bit] = '0'
    elif guard[bit] == '0':
        test_guard[bit] = '1'
    elif guard[bit] == 'X':
        test_guard[bit] = 'X'
    test_guard = ''.join(test_guard)
    return test_guard

def compare_obs(test_obs, existing_obs):
    if len(test_obs) != len(existing_obs):
        return False

    for i in range(len(test_obs)):
        if test_obs[i] == 'X' and existing_obs[i] == 'X':
            continue
        if test_obs[i] != existing_obs[i]:
            return False

    return True


def replace_guard_bit(guard, bit, lit):
    new_guard = list(guard)
    new_guard[bit] = lit
    new_guard = ''.join(new_guard)
    return new_guard